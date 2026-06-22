from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


NodeType = Literal["note", "tag", "entity", "folder"]
EdgeType = Literal["links_to", "backlinks_to", "has_tag", "mentions", "aliases", "in_folder"]


class ParsedWikilink(BaseModel):
    raw: str
    target: str
    alias: str = ""
    heading: str = ""
    embed: bool = False


class ParsedNote(BaseModel):
    key: str
    path: str
    title: str
    body: str
    content_preview: str = ""
    frontmatter: dict[str, Any] = Field(default_factory=dict)
    aliases: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    wikilinks: list[ParsedWikilink] = Field(default_factory=list)
    embeds: list[ParsedWikilink] = Field(default_factory=list)
    uri: str = ""


class ObsidianParseResult(BaseModel):
    vault_name: str
    notes: list[ParsedNote] = Field(default_factory=list)
    skipped: list[dict[str, Any]] = Field(default_factory=list)
    errors: list[dict[str, Any]] = Field(default_factory=list)


class KnowledgeGraphStats(BaseModel):
    sources: int = 0
    nodes: int = 0
    edges: int = 0
    notes: int = 0
    tags: int = 0
    entities: int = 0
    folders: int = 0
    last_import_at: Optional[datetime] = None


class KnowledgeSourceResponse(BaseModel):
    id: int
    source_type: str
    name: str
    source_uri: Optional[str] = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


class KnowledgeSourceDeleteResponse(BaseModel):
    source_id: int
    deleted: bool
    nodes: int = 0
    edges: int = 0
    import_jobs: int = 0


class KnowledgeImportJobResponse(BaseModel):
    id: int
    source_id: int
    status: str
    filename: str
    stats: dict[str, Any] = Field(default_factory=dict)
    error_message: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None


class KnowledgeNodeResponse(BaseModel):
    id: int
    source_id: int
    node_type: str
    key: str
    title: str
    content_preview: Optional[str] = None
    content: Optional[str] = None
    path: Optional[str] = None
    uri: Optional[str] = None
    properties: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


class KnowledgeEdgeResponse(BaseModel):
    id: int
    source_id: int
    from_node_id: int
    to_node_id: int
    edge_type: str
    weight: float = 1.0
    properties: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


class KnowledgeNeighborsResponse(BaseModel):
    center: KnowledgeNodeResponse
    nodes: list[KnowledgeNodeResponse]
    edges: list[KnowledgeEdgeResponse]


class KnowledgeSubgraphResponse(BaseModel):
    nodes: list[KnowledgeNodeResponse]
    edges: list[KnowledgeEdgeResponse]


class GraphRAGQueryResponse(BaseModel):
    query: str
    contexts: list[dict[str, Any]] = Field(default_factory=list)


class GraphRAGAnswerRequest(BaseModel):
    q: str = Field(..., min_length=1)
    limit: int = Field(5, ge=1, le=10)
    provider_id: str = ""
    model: str = ""


class GraphRAGAnswerResponse(BaseModel):
    query: str
    answer: str
    contexts: list[dict[str, Any]] = Field(default_factory=list)


class ObsidianImportStats(BaseModel):
    notes: int = 0
    tags: int = 0
    entities: int = 0
    folders: int = 0
    relations: int = 0
    skipped: int = 0
    errors: int = 0


class ObsidianImportResponse(BaseModel):
    job_id: int
    source_id: int
    status: str
    stats: ObsidianImportStats
    errors: list[dict[str, Any]] = Field(default_factory=list)
