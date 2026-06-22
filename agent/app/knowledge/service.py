from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Literal, Optional

import re
import shutil

from sqlalchemy import delete, func, or_, select, text

from app.core.config import settings
from app.core.database import async_session_factory
from app.knowledge.obsidian_importer import normalize_link_target, parse_obsidian_zip
from app.knowledge.schemas import (
    KnowledgeEdgeResponse,
    KnowledgeGraphStats,
    KnowledgeImportJobResponse,
    KnowledgeNeighborsResponse,
    KnowledgeNodeResponse,
    KnowledgeSourceResponse,
    KnowledgeSubgraphResponse,
    ObsidianImportResponse,
    ObsidianImportStats,
)
from app.models.knowledge_graph import KnowledgeChunk, KnowledgeEdge, KnowledgeImportJob, KnowledgeNode, KnowledgeSource


def _split_markdown_chunks(body: str, *, max_chars: int = 1200, overlap: int = 160) -> list[dict[str, str]]:
    normalized = (body or "").replace("\r\n", "\n").replace("\r", "\n").strip()
    if not normalized:
        return []
    sections: list[tuple[str, str]] = []
    current_heading = ""
    current_lines: list[str] = []
    for line in normalized.splitlines():
        heading = re.match(r"^(#{1,6})\s+(.+?)\s*$", line)
        if heading and current_lines:
            sections.append((current_heading, "\n".join(current_lines).strip()))
            current_lines = []
        if heading:
            current_heading = heading.group(2).strip()
        current_lines.append(line)
    if current_lines:
        sections.append((current_heading, "\n".join(current_lines).strip()))

    chunks: list[dict[str, str]] = []
    for heading, section in sections:
        text_value = section.strip()
        if not text_value:
            continue
        start = 0
        while start < len(text_value):
            end = min(len(text_value), start + max_chars)
            chunks.append({"heading": heading, "content": text_value[start:end].strip()})
            if end >= len(text_value):
                break
            start = max(0, end - overlap)
    return chunks


def _fts_query(q: str) -> str:
    tokens = [token for token in re.findall(r"[\w\u4e00-\u9fff-]+", q or "") if len(token) >= 2]
    if not tokens:
        return ""
    return " OR ".join(f'"{token}"' for token in tokens[:12])


def _safe_cache_path(source_id: int, note_path: str) -> Path:
    root = Path(settings.KNOWLEDGE_VAULT_CACHE_DIR).resolve()
    rel = PurePosixPath(note_path)
    parts = [part for part in rel.parts if part not in {"", ".", ".."}]
    target = (root / f"source-{source_id}" / Path(*parts)).resolve()
    source_root = (root / f"source-{source_id}").resolve()
    if source_root != target and source_root not in target.parents:
        raise ValueError("unsafe markdown cache path")
    return target


def _grep_terms(q: str) -> list[str]:
    terms = [token for token in re.findall(r"[\w\u4e00-\u9fff-]+", q or "") if len(token) >= 2]
    return list(dict.fromkeys(terms[:16]))


def _line_excerpt(lines: list[str], index: int, radius: int = 2) -> str:
    start = max(0, index - radius)
    end = min(len(lines), index + radius + 1)
    return "\n".join(lines[start:end]).strip()


def _node_to_response(node: KnowledgeNode) -> KnowledgeNodeResponse:
    return KnowledgeNodeResponse(
        id=node.id,
        source_id=node.source_id,
        node_type=node.node_type,
        key=node.key,
        title=node.title,
        content_preview=node.content_preview,
        content=node.content,
        path=node.path,
        uri=node.uri,
        properties=node.properties_json or {},
        created_at=node.created_at,
        updated_at=node.updated_at,
    )


def _edge_to_response(edge: KnowledgeEdge) -> KnowledgeEdgeResponse:
    return KnowledgeEdgeResponse(
        id=edge.id,
        source_id=edge.source_id,
        from_node_id=edge.from_node_id,
        to_node_id=edge.to_node_id,
        edge_type=edge.edge_type,
        weight=edge.weight,
        properties=edge.properties_json or {},
        created_at=edge.created_at,
    )


def _source_to_response(source: KnowledgeSource) -> KnowledgeSourceResponse:
    return KnowledgeSourceResponse(
        id=source.id,
        source_type=source.source_type,
        name=source.name,
        source_uri=source.source_uri,
        metadata=source.metadata_json or {},
        created_at=source.created_at,
        updated_at=source.updated_at,
    )


def _job_to_response(job: KnowledgeImportJob) -> KnowledgeImportJobResponse:
    return KnowledgeImportJobResponse(
        id=job.id,
        source_id=job.source_id,
        status=job.status,
        filename=job.filename,
        stats=job.stats_json or {},
        error_message=job.error_message,
        created_at=job.created_at,
        completed_at=job.completed_at,
    )


def _target_candidates(target: str) -> list[str]:
    normalized = normalize_link_target(target)
    candidates = [normalized]
    if normalized:
        path = PurePosixPath(normalized)
        candidates.append(str(path.with_suffix("")))
        candidates.append(path.stem.lower())
    return list(dict.fromkeys(c for c in candidates if c))


class KnowledgeGraphService:
    async def import_obsidian_zip(
        self,
        content: bytes,
        *,
        filename: str,
        source_name: str = "",
        replace: bool = False,
    ) -> ObsidianImportResponse:
        if not filename.lower().endswith(".zip"):
            raise ValueError("Only .zip files are accepted")
        if replace:
            # Reserved for future incremental sync; keeping the argument allows frontend/API compatibility.
            raise ValueError("replace import is not supported yet")

        parsed = parse_obsidian_zip(content, vault_name=source_name or "", filename=filename)
        now = datetime.now(timezone.utc)

        async with async_session_factory() as session:
            source = KnowledgeSource(
                source_type="obsidian",
                name=parsed.vault_name,
                source_uri=None,
                metadata_json={"filename": filename},
            )
            session.add(source)
            await session.flush()

            job = KnowledgeImportJob(
                source_id=source.id,
                status="running",
                filename=filename,
                stats_json={},
                created_at=now,
            )
            session.add(job)
            await session.flush()

            try:
                note_nodes: dict[str, KnowledgeNode] = {}
                note_lookup: dict[str, KnowledgeNode] = {}
                tag_nodes: dict[str, KnowledgeNode] = {}
                entity_nodes: dict[str, KnowledgeNode] = {}
                folder_nodes: dict[str, KnowledgeNode] = {}
                edge_keys: set[tuple[int, int, str]] = set()

                for note in parsed.notes:
                    node = KnowledgeNode(
                        source_id=source.id,
                        node_type="note",
                        key=note.key,
                        title=note.title,
                        content_preview=note.content_preview,
                        content=note.body,
                        path=note.path,
                        uri=note.uri,
                        properties_json={
                            "frontmatter": note.frontmatter,
                            "aliases": note.aliases,
                            "tags": note.tags,
                            "embeds": [embed.model_dump() for embed in note.embeds],
                        },
                    )
                    session.add(node)
                    note_nodes[note.key] = node
                await session.flush()

                source_root = Path(settings.KNOWLEDGE_VAULT_CACHE_DIR).resolve() / f"source-{source.id}"
                if source_root.exists():
                    shutil.rmtree(source_root)
                for note in parsed.notes:
                    target = _safe_cache_path(source.id, note.path)
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_text(note.body, encoding="utf-8")

                chunk_index = 0
                for note in parsed.notes:
                    node = note_nodes[note.key]
                    for chunk in _split_markdown_chunks(note.body):
                        session.add(KnowledgeChunk(
                            source_id=source.id,
                            node_id=node.id,
                            chunk_index=chunk_index,
                            heading=chunk["heading"],
                            content=chunk["content"],
                            path=note.path,
                            uri=note.uri,
                        ))
                        chunk_index += 1
                await session.flush()

                for note in parsed.notes:
                    node = note_nodes[note.key]
                    path_no_ext = str(PurePosixPath(note.path).with_suffix(""))
                    for key in {
                        note.path.lower(),
                        path_no_ext.lower(),
                        PurePosixPath(note.path).stem.lower(),
                        note.title.lower(),
                    }:
                        note_lookup.setdefault(key, node)
                    for alias in note.aliases:
                        note_lookup.setdefault(alias.lower(), node)

                async def get_tag_node(tag: str) -> KnowledgeNode:
                    key = tag.lower()
                    if key not in tag_nodes:
                        tag_nodes[key] = KnowledgeNode(
                            source_id=source.id,
                            node_type="tag",
                            key=key,
                            title=tag,
                            properties_json={},
                        )
                        session.add(tag_nodes[key])
                        await session.flush()
                    return tag_nodes[key]

                async def get_entity_node(name: str) -> KnowledgeNode:
                    key = normalize_link_target(name) or name.lower()
                    if key not in entity_nodes:
                        entity_nodes[key] = KnowledgeNode(
                            source_id=source.id,
                            node_type="entity",
                            key=key,
                            title=name.strip() or key,
                            properties_json={"source": "unresolved_wikilink"},
                        )
                        session.add(entity_nodes[key])
                        await session.flush()
                    return entity_nodes[key]

                async def get_folder_node(path: str) -> KnowledgeNode:
                    key = path.strip("/") or "/"
                    if key not in folder_nodes:
                        title = "Vault Root" if key == "/" else PurePosixPath(key).name
                        folder_nodes[key] = KnowledgeNode(
                            source_id=source.id,
                            node_type="folder",
                            key=key,
                            title=title,
                            path=None if key == "/" else key,
                            properties_json={"folder_path": key},
                        )
                        session.add(folder_nodes[key])
                        await session.flush()
                    return folder_nodes[key]

                async def add_edge(
                    from_node: KnowledgeNode,
                    to_node: KnowledgeNode,
                    edge_type: str,
                    properties: Optional[dict] = None,
                ) -> None:
                    key = (from_node.id, to_node.id, edge_type)
                    if key in edge_keys:
                        return
                    edge_keys.add(key)
                    session.add(
                        KnowledgeEdge(
                            source_id=source.id,
                            from_node_id=from_node.id,
                            to_node_id=to_node.id,
                            edge_type=edge_type,
                            weight=1.0,
                            properties_json=properties or {},
                        )
                    )

                for note in parsed.notes:
                    from_node = note_nodes[note.key]
                    folder_path = str(PurePosixPath(note.path).parent)
                    folder_node = await get_folder_node(folder_path if folder_path != "." else "/")
                    await add_edge(from_node, folder_node, "in_folder", {"path": folder_node.key})

                    for tag in note.tags:
                        tag_node = await get_tag_node(tag)
                        await add_edge(from_node, tag_node, "has_tag", {"tag": tag})

                    for link in note.wikilinks:
                        target_node = None
                        for candidate in _target_candidates(link.target):
                            target_node = note_lookup.get(candidate)
                            if target_node:
                                break
                        if target_node:
                            await add_edge(
                                from_node,
                                target_node,
                                "links_to",
                                {"raw": link.raw, "alias": link.alias, "heading": link.heading},
                            )
                            await add_edge(
                                target_node,
                                from_node,
                                "backlinks_to",
                                {"raw": link.raw, "alias": link.alias, "heading": link.heading},
                            )
                        else:
                            entity_node = await get_entity_node(link.alias or link.target)
                            await add_edge(
                                from_node,
                                entity_node,
                                "mentions",
                                {"raw": link.raw, "target": link.target, "alias": link.alias, "heading": link.heading},
                            )
                            await add_edge(
                                entity_node,
                                from_node,
                                "backlinks_to",
                                {"raw": link.raw, "target": link.target, "alias": link.alias, "heading": link.heading},
                            )

                await session.flush()
                stats = ObsidianImportStats(
                    notes=len(parsed.notes),
                    tags=len(tag_nodes),
                    entities=len(entity_nodes),
                    folders=len(folder_nodes),
                    relations=len(edge_keys),
                    skipped=len(parsed.skipped),
                    errors=len(parsed.errors),
                )
                job.status = "completed"
                job.completed_at = datetime.now(timezone.utc)
                job.stats_json = stats.model_dump()
                source.metadata_json = {
                    "filename": filename,
                    "skipped": parsed.skipped[:100],
                    "errors": parsed.errors[:100],
                }
                await session.commit()

                return ObsidianImportResponse(
                    job_id=job.id,
                    source_id=source.id,
                    status=job.status,
                    stats=stats,
                    errors=parsed.errors,
                )
            except Exception as exc:
                await session.rollback()
                try:
                    failed_source = KnowledgeSource(
                        source_type="obsidian",
                        name=parsed.vault_name,
                        source_uri=None,
                        metadata_json={"filename": filename},
                    )
                    session.add(failed_source)
                    await session.flush()
                    session.add(
                        KnowledgeImportJob(
                            source_id=failed_source.id,
                            status="failed",
                            filename=filename,
                            stats_json={},
                            error_message=str(exc),
                            created_at=now,
                            completed_at=datetime.now(timezone.utc),
                        )
                    )
                    await session.commit()
                except Exception:
                    await session.rollback()
                raise

    async def get_stats(self) -> KnowledgeGraphStats:
        async with async_session_factory() as session:
            sources = await session.scalar(select(func.count(KnowledgeSource.id))) or 0
            nodes = await session.scalar(select(func.count(KnowledgeNode.id))) or 0
            edges = await session.scalar(select(func.count(KnowledgeEdge.id))) or 0
            notes = await session.scalar(select(func.count(KnowledgeNode.id)).where(KnowledgeNode.node_type == "note")) or 0
            tags = await session.scalar(select(func.count(KnowledgeNode.id)).where(KnowledgeNode.node_type == "tag")) or 0
            entities = await session.scalar(select(func.count(KnowledgeNode.id)).where(KnowledgeNode.node_type == "entity")) or 0
            folders = await session.scalar(select(func.count(KnowledgeNode.id)).where(KnowledgeNode.node_type == "folder")) or 0
            last_import_at = await session.scalar(select(func.max(KnowledgeImportJob.completed_at)))
            return KnowledgeGraphStats(
                sources=sources,
                nodes=nodes,
                edges=edges,
                notes=notes,
                tags=tags,
                entities=entities,
                folders=folders,
                last_import_at=last_import_at,
            )

    async def list_sources(self) -> list[KnowledgeSourceResponse]:
        async with async_session_factory() as session:
            result = await session.execute(select(KnowledgeSource).order_by(KnowledgeSource.created_at.desc()))
            return [_source_to_response(source) for source in result.scalars().all()]

    async def delete_source(self, source_id: int) -> Optional[dict]:
        async with async_session_factory() as session:
            source = await session.get(KnowledgeSource, source_id)
            if not source:
                return None

            edge_count = await session.scalar(
                select(func.count(KnowledgeEdge.id)).where(KnowledgeEdge.source_id == source_id)
            ) or 0
            node_count = await session.scalar(
                select(func.count(KnowledgeNode.id)).where(KnowledgeNode.source_id == source_id)
            ) or 0
            job_count = await session.scalar(
                select(func.count(KnowledgeImportJob.id)).where(KnowledgeImportJob.source_id == source_id)
            ) or 0

            await session.execute(delete(KnowledgeChunk).where(KnowledgeChunk.source_id == source_id))
            await session.execute(delete(KnowledgeEdge).where(KnowledgeEdge.source_id == source_id))
            await session.execute(delete(KnowledgeNode).where(KnowledgeNode.source_id == source_id))
            await session.execute(delete(KnowledgeImportJob).where(KnowledgeImportJob.source_id == source_id))
            await session.execute(delete(KnowledgeSource).where(KnowledgeSource.id == source_id))
            await session.commit()
            cache_root = Path(settings.KNOWLEDGE_VAULT_CACHE_DIR).resolve() / f"source-{source_id}"
            shutil.rmtree(cache_root, ignore_errors=True)

            return {
                "source_id": source_id,
                "deleted": True,
                "nodes": node_count,
                "edges": edge_count,
                "import_jobs": job_count,
            }

    async def list_import_jobs(self, limit: int = 20, offset: int = 0) -> list[KnowledgeImportJobResponse]:
        async with async_session_factory() as session:
            stmt = select(KnowledgeImportJob).order_by(KnowledgeImportJob.created_at.desc()).offset(offset).limit(limit)
            result = await session.execute(stmt)
            return [_job_to_response(job) for job in result.scalars().all()]

    async def search_nodes(
        self,
        *,
        q: str = "",
        node_type: str = "",
        source_id: Optional[int] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[KnowledgeNodeResponse]:
        async with async_session_factory() as session:
            stmt = select(KnowledgeNode)
            if q:
                like = f"%{q}%"
                stmt = stmt.where(
                    or_(
                        KnowledgeNode.title.ilike(like),
                        KnowledgeNode.key.ilike(like),
                        KnowledgeNode.path.ilike(like),
                        KnowledgeNode.content_preview.ilike(like),
                        KnowledgeNode.content.ilike(like),
                    )
                )
            if node_type:
                stmt = stmt.where(KnowledgeNode.node_type == node_type)
            if source_id is not None:
                stmt = stmt.where(KnowledgeNode.source_id == source_id)
            stmt = stmt.order_by(KnowledgeNode.updated_at.desc(), KnowledgeNode.id.desc()).offset(offset).limit(limit)
            result = await session.execute(stmt)
            return [_node_to_response(node) for node in result.scalars().all()]

    async def search_chunks(self, q: str, *, limit: int = 12) -> list[dict]:
        query = (q or "").strip()
        if not query:
            return []
        safe_limit = max(1, min(limit, 50))
        fts = _fts_query(query)
        async with async_session_factory() as session:
            rows = []
            if fts:
                try:
                    result = await session.execute(
                        text(
                            """
                            SELECT c.id, c.node_id, c.source_id, c.chunk_index, c.heading, c.content,
                                   c.path, c.uri, n.title, n.key, n.node_type,
                                   bm25(knowledge_chunks_fts) AS score
                            FROM knowledge_chunks_fts
                            JOIN knowledge_chunks c ON c.id = knowledge_chunks_fts.rowid
                            JOIN knowledge_nodes n ON n.id = c.node_id
                            WHERE knowledge_chunks_fts MATCH :q
                            ORDER BY score
                            LIMIT :limit
                            """
                        ),
                        {"q": fts, "limit": safe_limit},
                    )
                    rows = result.mappings().all()
                except Exception:
                    rows = []
            if not rows:
                like = f"%{query}%"
                result = await session.execute(
                    select(KnowledgeChunk, KnowledgeNode)
                    .join(KnowledgeNode, KnowledgeNode.id == KnowledgeChunk.node_id)
                    .where(or_(
                        KnowledgeChunk.content.ilike(like),
                        KnowledgeChunk.heading.ilike(like),
                        KnowledgeNode.title.ilike(like),
                        KnowledgeNode.path.ilike(like),
                    ))
                    .limit(safe_limit)
                )
                out = []
                for chunk, node in result.all():
                    out.append({
                        "id": chunk.id,
                        "node_id": chunk.node_id,
                        "source_id": chunk.source_id,
                        "chunk_index": chunk.chunk_index,
                        "heading": chunk.heading,
                        "content": chunk.content,
                        "path": chunk.path,
                        "uri": chunk.uri,
                        "title": node.title,
                        "key": node.key,
                        "node_type": node.node_type,
                        "score": 0,
                    })
                return out
            return [dict(row) for row in rows]

    async def grep_markdown_files(self, q: str, *, limit: int = 12) -> list[dict]:
        terms = _grep_terms(q)
        if not terms:
            return []
        root = Path(settings.KNOWLEDGE_VAULT_CACHE_DIR).resolve()
        if not root.exists():
            return []
        matches: list[dict] = []
        lowered_terms = [term.lower() for term in terms]
        for path in sorted(root.glob("source-*")):
            if not path.is_dir():
                continue
            source_dir_path = path
            for md_path in sorted(source_dir_path.rglob("*")):
                if len(matches) >= limit:
                    break
                if not md_path.is_file() or md_path.suffix.lower() not in {".md", ".markdown"}:
                    continue
                try:
                    text_value = md_path.read_text(encoding="utf-8")
                except UnicodeDecodeError:
                    continue
                lines = text_value.splitlines()
                for idx, line in enumerate(lines):
                    lowered = line.lower()
                    hit_terms = [term for term in lowered_terms if term in lowered]
                    if not hit_terms:
                        continue
                    source_id = int(source_dir_path.name.replace("source-", "") or 0)
                    rel = md_path.relative_to(source_dir_path).as_posix()
                    matches.append({
                        "source_id": source_id,
                        "path": rel,
                        "line": idx + 1,
                        "terms": hit_terms,
                        "excerpt": _line_excerpt(lines, idx),
                        "read_chars": len(text_value),
                    })
                    break
            if len(matches) >= limit:
                break
        return matches[:limit]

    async def get_node(self, node_id: int) -> Optional[KnowledgeNodeResponse]:
        async with async_session_factory() as session:
            node = await session.get(KnowledgeNode, node_id)
            return _node_to_response(node) if node else None

    async def get_neighbors(
        self,
        node_id: int,
        *,
        depth: int = 1,
        direction: Literal["incoming", "outgoing", "both"] = "both",
        limit: int = 100,
    ) -> Optional[KnowledgeNeighborsResponse]:
        depth = max(1, min(depth, 2))
        async with async_session_factory() as session:
            center = await session.get(KnowledgeNode, node_id)
            if not center:
                return None

            seen_nodes = {center.id: center}
            seen_edges: dict[int, KnowledgeEdge] = {}
            frontier = {center.id}

            for _ in range(depth):
                if not frontier:
                    break
                conditions = []
                if direction in ("outgoing", "both"):
                    conditions.append(KnowledgeEdge.from_node_id.in_(frontier))
                if direction in ("incoming", "both"):
                    conditions.append(KnowledgeEdge.to_node_id.in_(frontier))
                stmt = select(KnowledgeEdge).where(or_(*conditions)).limit(limit)
                edge_result = await session.execute(stmt)
                edges = edge_result.scalars().all()
                next_frontier = set()
                for edge in edges:
                    seen_edges[edge.id] = edge
                    next_frontier.add(edge.from_node_id)
                    next_frontier.add(edge.to_node_id)
                next_frontier -= set(seen_nodes)
                if next_frontier:
                    node_result = await session.execute(select(KnowledgeNode).where(KnowledgeNode.id.in_(next_frontier)))
                    for node in node_result.scalars().all():
                        seen_nodes[node.id] = node
                frontier = next_frontier

            nodes = [node for node_id_key, node in seen_nodes.items() if node_id_key != center.id]
            return KnowledgeNeighborsResponse(
                center=_node_to_response(center),
                nodes=[_node_to_response(node) for node in nodes[:limit]],
                edges=[_edge_to_response(edge) for edge in list(seen_edges.values())[:limit]],
            )

    async def get_subgraph(
        self,
        *,
        q: str = "",
        node_id: Optional[int] = None,
        source_id: Optional[int] = None,
        depth: int = 1,
        limit: int = 100,
    ) -> KnowledgeSubgraphResponse:
        if node_id is not None:
            neighbors = await self.get_neighbors(node_id, depth=depth, limit=limit)
            if not neighbors:
                return KnowledgeSubgraphResponse(nodes=[], edges=[])
            return KnowledgeSubgraphResponse(nodes=[neighbors.center, *neighbors.nodes], edges=neighbors.edges)

        nodes = await self.search_nodes(q=q, source_id=source_id, limit=min(limit, 25))
        node_ids = {node.id for node in nodes}
        if not node_ids:
            return KnowledgeSubgraphResponse(nodes=[], edges=[])
        async with async_session_factory() as session:
            result = await session.execute(
                select(KnowledgeEdge)
                .where(or_(KnowledgeEdge.from_node_id.in_(node_ids), KnowledgeEdge.to_node_id.in_(node_ids)))
                .limit(limit)
            )
            edges = result.scalars().all()
            related_ids = set(node_ids)
            for edge in edges:
                related_ids.add(edge.from_node_id)
                related_ids.add(edge.to_node_id)
            node_result = await session.execute(select(KnowledgeNode).where(KnowledgeNode.id.in_(related_ids)).limit(limit))
            graph_nodes = node_result.scalars().all()
            return KnowledgeSubgraphResponse(
                nodes=[_node_to_response(node) for node in graph_nodes],
                edges=[_edge_to_response(edge) for edge in edges],
            )


knowledge_graph_service = KnowledgeGraphService()
