"""Lightweight GraphRAG retrieval over the persisted knowledge graph."""
from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any

from app.knowledge.schemas import KnowledgeNeighborsResponse, KnowledgeNodeResponse
from app.knowledge.service import knowledge_graph_service


def _content_excerpt(content: str, terms: list[str], max_chars: int = 1800) -> str:
    text = re.sub(r"\s+", " ", content or "").strip()
    if not text:
        return ""
    lowered = text.lower()
    best_idx = -1
    for term in terms:
        t = term.lower().strip()
        if len(t) < 2:
            continue
        idx = lowered.find(t)
        if idx >= 0:
            best_idx = idx
            break
    if best_idx < 0:
        return text[:max_chars] + ("..." if len(text) > max_chars else "")
    start = max(0, best_idx - max_chars // 3)
    end = min(len(text), start + max_chars)
    excerpt = text[start:end]
    if start > 0:
        excerpt = "..." + excerpt
    if end < len(text):
        excerpt += "..."
    return excerpt


@dataclass
class GraphRAGHit:
    """A graph node matched from the user query plus its local neighborhood."""

    node: KnowledgeNodeResponse
    neighbors: KnowledgeNeighborsResponse | None
    chunks: list[dict[str, Any]] | None = None

    def to_context(self, query_terms: list[str] | None = None) -> dict[str, Any]:
        edges = self.neighbors.edges if self.neighbors else []
        neighbor_nodes = self.neighbors.nodes if self.neighbors else []
        node_by_id = {node.id: node for node in neighbor_nodes}
        node_by_id[self.node.id] = self.node

        relations = []
        for edge in edges:
            from_node = node_by_id.get(edge.from_node_id)
            to_node = node_by_id.get(edge.to_node_id)
            relations.append({
                "type": edge.edge_type,
                "from": from_node.title if from_node else str(edge.from_node_id),
                "to": to_node.title if to_node else str(edge.to_node_id),
                "properties": edge.properties,
            })

        return {
            "node": {
                "id": self.node.id,
                "type": self.node.node_type,
                "title": self.node.title,
                "key": self.node.key,
                "path": self.node.path,
                "uri": self.node.uri,
                "preview": self.node.content_preview,
                "content_excerpt": _content_excerpt(self.node.content or self.node.content_preview or "", query_terms or []),
                "properties": self.node.properties,
            },
            "chunks": [
                {
                    "id": chunk.get("id"),
                    "heading": chunk.get("heading") or "",
                    "content": chunk.get("content") or "",
                    "path": chunk.get("path") or self.node.path,
                    "uri": chunk.get("uri") or self.node.uri,
                }
                for chunk in (self.chunks or [])[:4]
            ],
            "neighbors": [
                {
                    "id": node.id,
                    "type": node.node_type,
                    "title": node.title,
                    "key": node.key,
                    "path": node.path,
                    "preview": node.content_preview,
                }
                for node in neighbor_nodes
            ],
            "relations": relations,
        }


class GraphRAGRetriever:
    """Query the knowledge graph and return compact neighborhood context."""

    def __init__(self, max_seed_nodes: int = 3, neighbor_limit: int = 24):
        self.max_seed_nodes = max_seed_nodes
        self.neighbor_limit = neighbor_limit

    def _query_candidates(self, text: str) -> list[str]:
        normalized = re.sub(r"\s+", " ", text).strip()
        words = [word for word in re.findall(r"[\w\u4e00-\u9fff-]+", normalized) if len(word) >= 2]
        candidates = [normalized]
        if len(words) > 1:
            candidates.extend(" ".join(words[i:j]) for i in range(len(words)) for j in range(i + 2, min(len(words), i + 5) + 1))
        candidates.extend(words)
        cjk_text = "".join(re.findall(r"[\u4e00-\u9fff]+", normalized))
        if len(cjk_text) >= 2:
            for size in (4, 3, 2):
                candidates.extend(cjk_text[i:i + size] for i in range(0, max(0, len(cjk_text) - size + 1)))
        seen = set()
        ordered = []
        for candidate in candidates:
            key = candidate.lower()
            if key and key not in seen:
                seen.add(key)
                ordered.append(candidate)
        return ordered[:48]

    def _score_node(self, node: KnowledgeNodeResponse, query_text: str, candidates: list[str], chunks: list[dict[str, Any]] | None = None) -> float:
        haystacks = {
            "title": node.title or "",
            "key": node.key or "",
            "path": node.path or "",
            "preview": node.content_preview or "",
            "content": node.content or "",
        }
        lowered = {name: value.lower() for name, value in haystacks.items()}
        query = query_text.lower()
        score = 0.0
        if query and query in lowered["title"]:
            score += 20
        if query and query in lowered["key"]:
            score += 14
        if query and query in lowered["preview"]:
            score += 8
        if query and query in lowered["content"]:
            score += 6
        for candidate in candidates:
            c = candidate.lower()
            if not c:
                continue
            length_bonus = min(len(candidate), 12) / 12
            if c in lowered["title"]:
                score += 8 + length_bonus
            if c in lowered["key"]:
                score += 5 + length_bonus
            if c in lowered["path"]:
                score += 3 + length_bonus
            if c in lowered["preview"]:
                score += 2 + length_bonus
            if c in lowered["content"]:
                score += 1.5 + length_bonus
        if node.node_type == "note":
            score += 1
        if chunks:
            score += 12 + min(len(chunks), 4)
        return score

    async def query(self, text: str, *, max_hits: int | None = None) -> list[dict[str, Any]]:
        query_text = (text or "").strip()
        if not query_text:
            return []

        max_hits = max_hits or self.max_seed_nodes
        candidates = self._query_candidates(query_text)
        nodes_by_id: dict[int, KnowledgeNodeResponse] = {}
        chunks_by_node: dict[int, list[dict[str, Any]]] = {}
        file_matches = await knowledge_graph_service.grep_markdown_files(query_text, limit=max(max_hits * 3, 9))
        for chunk in await knowledge_graph_service.search_chunks(query_text, limit=max(max_hits * 4, 12)):
            node_id = int(chunk.get("node_id") or 0)
            if node_id:
                chunks_by_node.setdefault(node_id, []).append(chunk)

        for match in file_matches:
            source_id = match.get("source_id")
            path = match.get("path")
            if source_id and path:
                for node in await knowledge_graph_service.search_nodes(q=str(path), source_id=int(source_id), node_type="note", limit=1):
                    nodes_by_id.setdefault(node.id, node)
                    chunks_by_node.setdefault(node.id, []).append({
                        "id": None,
                        "heading": f"grep:{match.get('line')}",
                        "content": match.get("excerpt") or "",
                        "path": path,
                        "uri": node.uri,
                        "source": "markdown_grep",
                    })

        for candidate in candidates:
            for node in await knowledge_graph_service.search_nodes(q=candidate, limit=max(max_hits * 3, 10)):
                nodes_by_id.setdefault(node.id, node)
        for node_id in chunks_by_node:
            if node_id not in nodes_by_id:
                node = await knowledge_graph_service.get_node(node_id)
                if node:
                    nodes_by_id[node.id] = node

        ranked_nodes = sorted(
            nodes_by_id.values(),
            key=lambda node: self._score_node(node, query_text, candidates, chunks_by_node.get(node.id)),
            reverse=True,
        )

        contexts: list[dict[str, Any]] = []
        for node in ranked_nodes[:max_hits]:
            neighbors = await knowledge_graph_service.get_neighbors(node.id, depth=1, limit=self.neighbor_limit)
            contexts.append(GraphRAGHit(node=node, neighbors=neighbors, chunks=chunks_by_node.get(node.id, [])).to_context(candidates))
        if contexts:
            contexts[0]["retrieval_steps"] = [
                {"step": "grep_markdown_files", "matches": len(file_matches)},
                {"step": "read_markdown_files", "files": len({m.get("path") for m in file_matches})},
                {"step": "search_chunks_fts", "matches": sum(len(v) for v in chunks_by_node.values())},
                {"step": "expand_wikilink_graph", "nodes": len(contexts)},
            ]
            contexts[0]["file_matches"] = file_matches[:10]
        return contexts


graph_retriever = GraphRAGRetriever()
