# Development Guide

## Setup

### Prerequisites
- Go >= 1.23
- Python >= 3.11
- SQLite >= 3.40

### Install Dependencies

```bash
# Go
GOPROXY=https://goproxy.cn,direct go mod tidy

# Python
cd agent
pip install fastapi uvicorn langgraph langchain-core openai \
  pydantic-settings sqlalchemy aiosqlite redis httpx \
  "python-jose[cryptography]" passlib numpy pytest pytest-asyncio
```

### Environment Variables

Create `agent/.env`:
```bash
LLM_API_KEY=sk-xxx
LLM_BASE_URL=https://api.openai.com/v1
LLM_MODEL=gpt-4o-mini
BRAVE_API_KEY=your-brave-api-key
```

## Running

```bash
# Terminal 1: Python Agent
cd agent
python main.py  # starts on :8001

# Terminal 2: Go Gateway
cd cmd/gateway
go run main.go  # starts on :8080
```

## Testing

```bash
# Go tests
go test ./...

# Python tests  
cd agent && pytest tests/ -v

# All tests
bash scripts/run_tests.sh
```

## Adding a New Tool

1. Create tool in `internal/service/tool/builtin/`
2. Implement `Name()`, `Description()`, `InputSchema()`, `Execute()`
3. Register in `internal/api/router.go`

## Adding a New LangGraph Node

1. Create node in `agent/app/graph/nodes/`
2. Add to graph in `agent/app/graph/graph.py`
3. Add edges in `agent/app/graph/edges.py`
