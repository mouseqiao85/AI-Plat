from __future__ import annotations

import os
import sys
import zipfile
from io import BytesIO

import httpx
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.core.database import Base
from app.knowledge.service import knowledge_graph_service
from app.models.knowledge_graph import KnowledgeChunk
import app.knowledge.service as service_module
import app.models  # noqa: F401 - ensure SQLAlchemy models are registered
from sqlalchemy import select, func


def _zip(entries: dict[str, str]) -> bytes:
    buf = BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for name, content in entries.items():
            zf.writestr(name, content)
    return buf.getvalue()


@pytest_asyncio.fixture()
async def kg_db(tmp_path, monkeypatch):
    db_path = tmp_path / "kg.db"
    monkeypatch.setattr("app.core.config.settings.KNOWLEDGE_VAULT_CACHE_DIR", str(tmp_path / "vault_cache"))
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    monkeypatch.setattr(service_module, "async_session_factory", session_factory)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


@pytest.mark.asyncio
async def test_import_obsidian_zip_stats_search_and_neighbors(kg_db):
    payload = _zip({
        "Index.md": """---
title: Agent Platform
tags: [csm]
---
# Agent Platform
Linked to [[Projects/CSM-27|CSM 27]] and [[Unresolved Concept]].
#agent-platform
""",
        "Projects/CSM-27.md": "# CSM-27\nKnowledge graph storage.",
        ".obsidian/app.json": "{}",
    })

    result = await knowledge_graph_service.import_obsidian_zip(
        payload,
        filename="vault.zip",
        source_name="Vault",
    )

    assert result.status == "completed"
    assert result.stats.notes == 2
    assert result.stats.tags == 2
    assert result.stats.entities == 1
    assert result.stats.folders == 2
    assert result.stats.relations == 8
    assert result.stats.skipped >= 1

    stats = await knowledge_graph_service.get_stats()
    assert stats.sources == 1
    assert stats.notes == 2
    assert stats.tags == 2
    assert stats.entities == 1
    assert stats.folders == 2
    assert stats.edges == 8

    nodes = await knowledge_graph_service.search_nodes(q="CSM")
    assert any(node.node_type == "note" and node.title == "CSM-27" for node in nodes)
    chunks = await knowledge_graph_service.search_chunks("Knowledge graph storage")
    assert chunks
    assert chunks[0]["title"] == "CSM-27"

    index_note = (await knowledge_graph_service.search_nodes(q="Agent Platform", node_type="note"))[0]
    assert index_note.properties["frontmatter"]["title"] == "Agent Platform"

    index_nodes = await knowledge_graph_service.search_nodes(q="Agent Platform", node_type="note")
    neighbors = await knowledge_graph_service.get_neighbors(index_nodes[0].id)
    assert neighbors is not None
    edge_types = {edge.edge_type for edge in neighbors.edges}
    assert {"links_to", "mentions", "has_tag", "backlinks_to", "in_folder"}.issubset(edge_types)
    assert any(node.title == "Unresolved Concept" and node.node_type == "entity" for node in neighbors.nodes)
    assert any(node.title == "Vault Root" and node.node_type == "folder" for node in neighbors.nodes)


@pytest.mark.asyncio
async def test_import_obsidian_frontmatter_date_values_are_persisted(kg_db):
    payload = _zip({
        "Dated.md": """---
title: Dated Note
created: 2026-06-05
review:
  due: 2026-06-06
---
# Dated Note
""",
    })

    result = await knowledge_graph_service.import_obsidian_zip(
        payload,
        filename="vault.zip",
        source_name="Vault",
    )

    assert result.status == "completed"
    nodes = await knowledge_graph_service.search_nodes(q="Dated Note", node_type="note")
    assert nodes[0].properties["frontmatter"]["created"] == "2026-06-05"
    assert nodes[0].properties["frontmatter"]["review"]["due"] == "2026-06-06"


@pytest.mark.asyncio
async def test_delete_knowledge_source_removes_graph_and_jobs(kg_db):
    payload = _zip({
        "Index.md": "# Index\n[[Target]]\n#tag",
        "Target.md": "# Target\n",
    })

    result = await knowledge_graph_service.import_obsidian_zip(
        payload,
        filename="vault.zip",
        source_name="Vault",
    )

    before = await knowledge_graph_service.get_stats()
    assert before.sources == 1
    assert before.nodes > 0
    assert before.edges > 0

    deleted = await knowledge_graph_service.delete_source(result.source_id)
    assert deleted == {
        "source_id": result.source_id,
        "deleted": True,
        "nodes": before.nodes,
        "edges": before.edges,
        "import_jobs": 1,
    }

    after = await knowledge_graph_service.get_stats()
    assert after.sources == 0
    assert after.nodes == 0
    assert after.edges == 0
    assert await knowledge_graph_service.delete_source(result.source_id) is None
    async with service_module.async_session_factory() as session:
        assert await session.scalar(select(func.count(KnowledgeChunk.id))) == 0


@pytest.mark.asyncio
async def test_import_obsidian_rejects_non_zip(kg_db):
    with pytest.raises(ValueError, match="Only .zip"):
        await knowledge_graph_service.import_obsidian_zip(b"hello", filename="notes.md", source_name="Vault")


@pytest.mark.asyncio
async def test_import_obsidian_preserves_folder_hierarchy_and_backlinks(kg_db):
    payload = _zip({
        "Areas/Product/Index.md": "# Product Index\n[[Specs/Roadmap]]",
        "Specs/Roadmap.md": "# Roadmap\n",
    })

    result = await knowledge_graph_service.import_obsidian_zip(
        payload,
        filename="vault.zip",
        source_name="Vault",
    )

    assert result.stats.folders == 2
    assert result.stats.relations == 4

    folders = await knowledge_graph_service.search_nodes(node_type="folder")
    folder_keys = {folder.key for folder in folders}
    assert {"Areas/Product", "Specs"}.issubset(folder_keys)

    roadmap = (await knowledge_graph_service.search_nodes(q="Roadmap", node_type="note"))[0]
    neighbors = await knowledge_graph_service.get_neighbors(roadmap.id)
    assert neighbors is not None
    edge_types = {edge.edge_type for edge in neighbors.edges}
    assert {"backlinks_to", "in_folder"}.issubset(edge_types)
    assert any(node.title == "Product Index" for node in neighbors.nodes)
    assert any(node.key == "Specs" and node.node_type == "folder" for node in neighbors.nodes)


@pytest.mark.asyncio
async def test_knowledge_graph_api_upload_and_query(kg_db):
    from app.api.knowledge_graph_routes import router
    from fastapi import FastAPI

    app = FastAPI()
    app.include_router(router)
    payload = _zip({"Index.md": "# Index\n[[Target]]\n#tag"})

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        bad = await client.post(
            "/api/v1/knowledge-graph/import/obsidian",
            files={"file": ("notes.md", b"hello", "text/markdown")},
        )
        assert bad.status_code == 400

        ok = await client.post(
            "/api/v1/knowledge-graph/import/obsidian",
            data={"source_name": "Vault"},
            files={"file": ("vault.zip", payload, "application/zip")},
        )
        assert ok.status_code == 200, ok.text
        assert ok.json()["stats"]["notes"] == 1

        stats = await client.get("/api/v1/knowledge-graph/stats")
        assert stats.status_code == 200
        assert stats.json()["entities"] == 1

        nodes = await client.get("/api/v1/knowledge-graph/nodes?q=Index")
        assert nodes.status_code == 200
        assert nodes.json()[0]["title"] == "Index"

        graphrag = await client.get("/api/v1/knowledge-graph/graphrag?q=Index&limit=1")
        assert graphrag.status_code == 200
        assert graphrag.json()["query"] == "Index"
        assert graphrag.json()["contexts"][0]["node"]["title"] == "Index"

        source_id = ok.json()["source_id"]
        deleted = await client.delete(f"/api/v1/knowledge-graph/sources/{source_id}")
        assert deleted.status_code == 200
        assert deleted.json()["deleted"] is True
        assert deleted.json()["nodes"] > 0

        missing = await client.delete(f"/api/v1/knowledge-graph/sources/{source_id}")
        assert missing.status_code == 404
