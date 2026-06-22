from __future__ import annotations

import os
import sys
import zipfile
from io import BytesIO

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.core.database import Base
from app.graph.nodes.rag_retrieval import rag_retrieval_node
from app.knowledge.service import knowledge_graph_service
from app.rag.graphrag import GraphRAGRetriever
from app.rag.retriever import retriever
import app.knowledge.service as service_module
import app.models  # noqa: F401 - ensure SQLAlchemy models are registered


def _zip(entries: dict[str, str]) -> bytes:
    buf = BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for name, content in entries.items():
            zf.writestr(name, content)
    return buf.getvalue()


@pytest_asyncio.fixture()
async def kg_db(tmp_path, monkeypatch):
    db_path = tmp_path / "graphrag.db"
    monkeypatch.setattr("app.core.config.settings.KNOWLEDGE_VAULT_CACHE_DIR", str(tmp_path / "vault_cache"))
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    monkeypatch.setattr(service_module, "async_session_factory", session_factory)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    retriever.clear()
    yield
    retriever.clear()
    await engine.dispose()


@pytest.mark.asyncio
async def test_graphrag_empty_graph_returns_no_context(kg_db):
    graph = GraphRAGRetriever()

    assert await graph.query("missing") == []


@pytest.mark.asyncio
async def test_graphrag_no_entity_match_returns_no_context(kg_db):
    payload = _zip({"Index.md": "# Agent Platform\n[[GraphRAG]]"})
    await knowledge_graph_service.import_obsidian_zip(payload, filename="vault.zip", source_name="Vault")

    graph = GraphRAGRetriever()

    assert await graph.query("unrelated-market-topic") == []


@pytest.mark.asyncio
async def test_graphrag_returns_neighbors_for_matching_node(kg_db):
    payload = _zip({
        "Index.md": "# Index\nSee [[Agent Platform]] and [[GraphRAG]].",
        "Agent Platform.md": "# Agent Platform\nKnowledge graph platform.",
        "GraphRAG.md": "# GraphRAG\nGraph enhanced retrieval.",
    })
    await knowledge_graph_service.import_obsidian_zip(payload, filename="vault.zip", source_name="Vault")

    graph = GraphRAGRetriever(max_seed_nodes=2)
    contexts = await graph.query("请介绍一下 Agent Platform")

    assert len(contexts) >= 1
    assert contexts[0]["node"]["title"] == "Agent Platform"
    assert any(rel["type"] == "links_to" for ctx in contexts for rel in ctx["relations"])


@pytest.mark.asyncio
async def test_graphrag_supports_multiple_entity_hits(kg_db):
    payload = _zip({
        "A.md": "# Alpha Architecture\n[[Shared Entity]]",
        "B.md": "# Alpha Operations\n[[Shared Entity]]",
    })
    await knowledge_graph_service.import_obsidian_zip(payload, filename="vault.zip", source_name="Vault")

    graph = GraphRAGRetriever(max_seed_nodes=3)
    contexts = await graph.query("Alpha")

    titles = {ctx["node"]["title"] for ctx in contexts}
    assert {"Alpha Architecture", "Alpha Operations"}.issubset(titles)


@pytest.mark.asyncio
async def test_graphrag_searches_full_markdown_content(kg_db):
    payload = _zip({
        "Roadmap.md": "# Roadmap\nThis note explains the customer success motion and renewal playbook in detail.",
    })
    await knowledge_graph_service.import_obsidian_zip(payload, filename="vault.zip", source_name="Vault")

    graph = GraphRAGRetriever(max_seed_nodes=2)
    contexts = await graph.query("renewal playbook")

    assert contexts
    assert contexts[0]["node"]["title"] == "Roadmap"
    assert contexts[0]["retrieval_steps"][0]["step"] == "grep_markdown_files"
    assert contexts[0]["file_matches"]
    assert contexts[0]["file_matches"][0]["path"] == "Roadmap.md"
    assert contexts[0]["chunks"]
    assert "renewal playbook" in contexts[0]["chunks"][0]["content"]
    assert "renewal playbook" in contexts[0]["node"]["content_excerpt"]


@pytest.mark.asyncio
async def test_rag_retrieval_node_injects_graph_context_without_vector_docs(kg_db):
    payload = _zip({"Index.md": "# Agent Platform\n[[GraphRAG]]\n#csm"})
    await knowledge_graph_service.import_obsidian_zip(payload, filename="vault.zip", source_name="Vault")

    out = await rag_retrieval_node({
        "messages": [{"role": "user", "content": "Agent Platform"}],
        "context": None,
    })

    assert out["retrieved_docs"] == []
    assert out["context"]["graphrag"]["hit_count"] >= 1
    assert out["context"]["knowledge_graph"][0]["node"]["title"] == "Agent Platform"
