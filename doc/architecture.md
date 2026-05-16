# Agent Platform Architecture

## Overview

Mixed-architecture AI Agent framework: **Golang API Gateway** + **Python LangGraph Agent Service**.

## Design Decisions

### HTTP over gRPC for MVP
- HTTP is simpler to debug with curl
- SSE streaming proxies naturally over HTTP
- gRPC proto definitions prepared for future upgrade
- When performance demands it, gRPC can be swapped in

### Tool Execution on Go Side
- Better concurrency for I/O-bound tools (web search, etc.)
- Tools reusable by other Go services
- Python calls Go via HTTP for tool execution

### SQLite for Development, PostgreSQL for Production
- SQLite: single-file, zero-config for local dev
- PostgreSQL + pgvector: production-grade with vector search
- Switch via config file, no code changes needed

## Data Flow

```
1. User sends message → Go Gateway (HTTP POST /api/v1/chat)
2. Go authenticates (JWT), loads conversation history
3. Go sends request → Python Agent (HTTP POST /api/v1/agent/chat/stream)
4. Python LangGraph executes:
   a. Input validation
   b. Intent routing (chat → responder, task → planner)
   c. RAG retrieval (if needed)
   d. Task planning → scope check → tool execution
   e. Response generation
   f. Output validation
5. Python streams events back → Go SSE to client
6. Go saves messages to SQLite
```

## Component Responsibilities

### Go Gateway
- HTTP REST API + SSE streaming
- JWT authentication and authorization
- Session and conversation management
- Tool registry with execution timeout
- Message persistence
- Rate limiting and metrics

### Python Agent
- LangGraph StateGraph execution
- LLM calls (OpenAI-compatible API)
- Input/output safety validation
- Scope-based permission checking
- RAG document retrieval
- Tool callback to Go for execution
- Checkpointer for state persistence
