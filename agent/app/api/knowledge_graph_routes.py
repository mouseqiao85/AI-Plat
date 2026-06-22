"""Knowledge graph API routes for Obsidian imports and graph queries."""
from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile

from app.knowledge.schemas import (
    GraphRAGAnswerRequest,
    GraphRAGAnswerResponse,
    KnowledgeGraphStats,
    KnowledgeImportJobResponse,
    KnowledgeNeighborsResponse,
    KnowledgeNodeResponse,
    KnowledgeSourceDeleteResponse,
    KnowledgeSourceResponse,
    KnowledgeSubgraphResponse,
    GraphRAGQueryResponse,
    ObsidianImportResponse,
)
from app.core.config import settings
from app.llm.client import build_llm_client, chat_completion
from app.knowledge.service import knowledge_graph_service
from app.rag.graphrag import graph_retriever

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/knowledge-graph", tags=["knowledge-graph"])


@router.post("/import/obsidian", response_model=ObsidianImportResponse)
async def import_obsidian(
    file: UploadFile = File(...),
    source_name: str = Form(""),
    replace: bool = Form(False),
):
    """Import an Obsidian vault zip into the knowledge graph."""
    if not file.filename or not file.filename.lower().endswith(".zip"):
        raise HTTPException(status_code=400, detail="Only .zip files are accepted")
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded zip is empty")
    try:
        return await knowledge_graph_service.import_obsidian_zip(
            content,
            filename=file.filename,
            source_name=source_name,
            replace=replace,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("obsidian import failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/stats", response_model=KnowledgeGraphStats)
async def get_stats():
    return await knowledge_graph_service.get_stats()


@router.get("/sources", response_model=list[KnowledgeSourceResponse])
async def list_sources():
    return await knowledge_graph_service.list_sources()


@router.delete("/sources/{source_id}", response_model=KnowledgeSourceDeleteResponse)
async def delete_source(source_id: int):
    result = await knowledge_graph_service.delete_source(source_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Knowledge source not found")
    return result


@router.get("/import-jobs", response_model=list[KnowledgeImportJobResponse])
async def list_import_jobs(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    return await knowledge_graph_service.list_import_jobs(limit=limit, offset=offset)


@router.get("/nodes", response_model=list[KnowledgeNodeResponse])
async def search_nodes(
    q: str = "",
    node_type: str = "",
    source_id: Optional[int] = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    if node_type and node_type not in {"note", "tag", "entity", "folder"}:
        raise HTTPException(status_code=400, detail="node_type must be note, tag, entity, or folder")
    return await knowledge_graph_service.search_nodes(
        q=q,
        node_type=node_type,
        source_id=source_id,
        limit=limit,
        offset=offset,
    )


@router.get("/nodes/{node_id}", response_model=KnowledgeNodeResponse)
async def get_node(node_id: int):
    node = await knowledge_graph_service.get_node(node_id)
    if not node:
        raise HTTPException(status_code=404, detail="Knowledge node not found")
    return node


@router.get("/nodes/{node_id}/neighbors", response_model=KnowledgeNeighborsResponse)
async def get_neighbors(
    node_id: int,
    depth: int = Query(1, ge=1, le=2),
    direction: str = Query("both", pattern="^(incoming|outgoing|both)$"),
    limit: int = Query(100, ge=1, le=500),
):
    neighbors = await knowledge_graph_service.get_neighbors(
        node_id,
        depth=depth,
        direction=direction,  # type: ignore[arg-type]
        limit=limit,
    )
    if not neighbors:
        raise HTTPException(status_code=404, detail="Knowledge node not found")
    return neighbors


@router.get("/subgraph", response_model=KnowledgeSubgraphResponse)
async def get_subgraph(
    q: str = "",
    node_id: Optional[int] = None,
    source_id: Optional[int] = None,
    depth: int = Query(1, ge=1, le=2),
    limit: int = Query(100, ge=1, le=500),
):
    return await knowledge_graph_service.get_subgraph(
        q=q,
        node_id=node_id,
        source_id=source_id,
        depth=depth,
        limit=limit,
    )


@router.get("/graphrag", response_model=GraphRAGQueryResponse)
async def query_graphrag(
    q: str = Query(..., min_length=1),
    limit: int = Query(3, ge=1, le=10),
):
    query_text = q.strip()
    if not query_text:
        raise HTTPException(status_code=400, detail="q cannot be empty")
    contexts = await graph_retriever.query(query_text, max_hits=limit)
    return {"query": query_text, "contexts": contexts}


def _context_to_text(contexts: list[dict], max_chars: int = 12000) -> str:
    blocks: list[str] = []
    for idx, context in enumerate(contexts, 1):
        node = context.get("node") or {}
        lines = [
            f"[{idx}] {node.get('title') or node.get('key') or node.get('id')}",
            f"类型: {node.get('type') or ''}",
        ]
        if context.get("retrieval_steps"):
            lines.append(f"检索过程: {context.get('retrieval_steps')}")
        if context.get("file_matches"):
            lines.append("Markdown grep/read 命中:")
            for match in (context.get("file_matches") or [])[:5]:
                lines.append(f"- {match.get('path')}:{match.get('line')} {match.get('excerpt')}")
        if node.get("path"):
            lines.append(f"路径: {node.get('path')}")
        chunks = context.get("chunks") or []
        if chunks:
            lines.append("命中片段:")
            for chunk in chunks[:4]:
                heading = chunk.get("heading") or ""
                prefix = f"- {heading}: " if heading else "- "
                lines.append(f"{prefix}{chunk.get('content') or ''}")
        elif node.get("content_excerpt"):
            lines.append(f"正文片段: {node.get('content_excerpt')}")
        elif node.get("preview"):
            lines.append(f"内容摘要: {node.get('preview')}")
        relations = context.get("relations") or []
        if relations:
            lines.append("关系:")
            for rel in relations[:10]:
                lines.append(f"- {rel.get('from')} --{rel.get('type')}--> {rel.get('to')}")
        neighbors = context.get("neighbors") or []
        if neighbors:
            titles = [n.get("title") for n in neighbors[:10] if n.get("title")]
            if titles:
                lines.append(f"相邻节点: {'、'.join(titles)}")
        blocks.append("\n".join(lines))
    text = "\n\n".join(blocks)
    if len(text) > max_chars:
        text = text[:max_chars] + "\n\n[上下文已截断]"
    return text


@router.post("/graphrag/answer", response_model=GraphRAGAnswerResponse)
async def answer_graphrag(request: GraphRAGAnswerRequest):
    query_text = request.q.strip()
    if not query_text:
        raise HTTPException(status_code=400, detail="q cannot be empty")

    contexts = await graph_retriever.query(query_text, max_hits=request.limit)
    if not contexts:
        return {
            "query": query_text,
            "answer": f"知识库中没有检索到与「{query_text}」直接相关的内容。可以尝试更具体的关键词，或先导入相关资料。",
            "contexts": [],
        }

    context_text = _context_to_text(contexts)
    messages = [
        {
            "role": "system",
            "content": (
                "你是企业知识库问答助手。只基于给定的 GraphRAG 知识图谱上下文回答。"
                "如果上下文不足，要明确说明不足，不要编造。回答使用中文，结构清晰，先给结论，再列依据。"
            ),
        },
        {
            "role": "user",
            "content": f"问题：{query_text}\n\nGraphRAG 知识图谱上下文：\n{context_text}",
        },
    ]
    try:
        client = build_llm_client(provider_id=request.provider_id, model=request.model)
        response = await chat_completion(
            client,
            model=request.model or settings.LLM_MODEL,
            messages=messages,
            provider_id=request.provider_id,
            temperature=0.2,
            max_tokens=1800,
        )
        answer = response.content.strip() or "模型未生成有效答案。"
    except Exception as exc:
        logger.exception("graphrag answer generation failed")
        answer = (
            "已完成知识库检索，但调用大模型组织答案失败。\n\n"
            f"错误：{exc}\n\n"
            f"检索上下文：\n{context_text[:4000]}"
        )

    return {"query": query_text, "answer": answer, "contexts": contexts}
