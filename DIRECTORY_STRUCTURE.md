# Agent Platform Directory Structure

This repository contains a Go gateway, a Python agent service, a Hermes bridge service, and a React web client.

## Root

Keep root-level files limited to project entry points and top-level metadata:

- `README.md` - project overview and quick start.
- `Makefile` - common development commands.
- `docker-compose.yml` - local compose entry point.
- `go.mod`, `go.sum` - Go module files.
- `.env.example` - root environment template.
- `start.ps1` - Windows local startup helper.
- `DIRECTORY_STRUCTURE.md` - this structure guide.

Local secrets, runtime output, caches, and generated archives are ignored by `.gitignore`.

## Source Code

- `cmd/gateway/` - Go gateway entry point.
- `internal/` - Go API handlers, services, middleware, models, and stores.
- `pkg/` - shared Go packages.
- `agent/` - Python FastAPI/LangGraph agent service.
- `hermes-bridge/` - Python bridge service for Hermes CLI and multi-agent flows.
- `web/` - React/Vite frontend.
- `proto/` - protocol definitions and design references.

## Configuration And Deployment

- `configs/` - shared service configuration.
- `deployments/` - Docker, Kubernetes, and Prometheus deployment assets.
- `scripts/` - automation and operational scripts.
- `scripts/deploy/` - active deployment, verification, and remote maintenance scripts.
- `server_deployment/` - server-side setup helpers.

## Documentation

- `doc/` - active product, architecture, design, and planning documents.
- `doc/prd/` - PRD and product requirement documents.
- `doc/reports/` - audit, verification, and fix reports.
- `doc/ue/` - UX/UI reference images and prompts.
- `doc/history/` - older documentation kept for reference.

## Runtime And Generated Content

The following directories are runtime/generated and should not be treated as primary source:

- `data/` - local database and uploaded data.
- `outputs/` - generated outputs.
- `.claude/` and nested `.claude/` directories - local assistant/tool state.
- `.pytest_cache/`, `__pycache__/`, `node_modules/`, `web/dist/`, and archive files.

## Placement Rules

- Put new Go gateway code under `cmd/`, `internal/`, or `pkg/` according to existing package boundaries.
- Put new Python agent code under `agent/app/` and tests under `agent/tests/`.
- Put new Hermes bridge code under `hermes-bridge/bridge/` and tests under `hermes-bridge/tests/`.
- Put new frontend code under `web/src/`.
- Put new deployment scripts under `scripts/deploy/` when they use shared SSH/deploy helpers.
- Put new docs under the matching `doc/` subdirectory instead of the repository root.
