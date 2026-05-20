# Project PRD — Document Analyst Monorepo

## 1. Overview

A full-stack monorepo for a domain-agnostic document analyst powered by a multi-agent LangGraph supervisor with streaming responses. Users upload documents, ask questions, and get AI-powered answers via RAG + web research + synthesis.

The monorepo houses all shared libraries, agent definitions, tools, API contracts, the FastAPI backend, and the Next.js frontend — enabling code reuse, atomic changes, and a single CI/CD pipeline.

---

## 2. Monorepo Structure

```
doc-analyst/
├── pyproject.toml                   # uv workspace root
├── uv.lock                         # single Python lockfile (auto-generated)
├── package.json                     # pnpm workspace root
├── pnpm-workspace.yaml              # pnpm workspace config
├── docker-compose.yml               # local dev stack
├── Makefile                         # dev commands
├── .env                             # shared env vars
├── .gitignore
├── .python-version                  # Python version pin (3.11+)
│
├── apps/
│   ├── api/                         # FastAPI backend (see be/backend.prd.md)
│   │   ├── pyproject.toml           # depends on packages/core, agents, tools, contracts
│   │   └── app/                     # application code
│   │
│   └── web/                         # Next.js frontend (see fe/frontend.prd.md)
│       ├── package.json             # depends on @doc-analyst/contracts
│       └── app/                     # Next.js app router
│
├── packages/
│   ├── core/                        # Shared Python utilities (reusable across any project)
│   │   ├── pyproject.toml
│   │   └── core/
│   │       ├── __init__.py
│   │       ├── patterns.py          # @singleton decorator (thread-safe, double-checked locking)
│   │       ├── retry.py             # @retryable + circuit breakers (tenacity + pybreaker)
│   │       ├── llm_context_manager.py  # Token budget management via litellm
│   │       └── embedding.py         # EmbeddingStrategy protocol + AzureOpenAIEmbedding
│   │
│   ├── agents/                      # Reusable agent definitions
│   │   ├── pyproject.toml           # depends on packages/core, packages/tools
│   │   └── agents/
│   │       ├── __init__.py
│   │       ├── registry.py          # @singleton AgentRegistry
│   │       ├── factory.py           # AgentFactory (consistent agent creation)
│   │       ├── supervisor.py        # create_supervisor wrapper
│   │       ├── pdf_agent.py         # Document retrieval agent (RAG via LanceDB)
│   │       ├── research_agent.py    # Web research agent (Tavily)
│   │       └── analyzer_agent.py    # Synthesis/reasoning agent (LLM-only)
│   │
│   ├── tools/                       # Reusable tool functions (decoupled from agents)
│   │   ├── pyproject.toml           # depends on packages/core
│   │   └── tools/
│   │       ├── __init__.py
│   │       ├── pdf_tools.py         # search_document, get_page, list_documents
│   │       ├── web_tools.py         # tavily_search
│   │       └── analysis_tools.py    # compare, summarize (instructor-backed structured outputs)
│   │
│   └── contracts/                   # Shared API types — single source of truth
│       ├── pyproject.toml           # Python side (Pydantic models)
│       ├── package.json             # @doc-analyst/contracts (TypeScript side)
│       ├── contracts/
│       │   ├── __init__.py
│       │   ├── events.py            # SSE event types: TokenEvent, AgentStartEvent, etc.
│       │   ├── requests.py          # ChatRequest, UploadResponse, FileMetadata
│       │   └── schemas.py           # DocumentChunk, ParsedDocument, SearchResult
│       └── src/
│           └── index.ts             # TypeScript mirror of Python types
│
└── docs/                            # PRDs live here (moved from fe/ and be/)
    ├── project.prd.md               # This file (monorepo overview)
    ├── backend.prd.md               # Backend-specific PRD
    └── frontend.prd.md              # Frontend-specific PRD
```

---

## 3. Package Dependency Graph

```
apps/api  ─────► packages/core        (patterns, retry, LLMContextManager)
          ─────► packages/agents       (supervisor, pdf_agent, research_agent, analyzer_agent)
          ─────► packages/tools        (pdf_tools, web_tools, analysis_tools)
          ─────► packages/contracts    (Pydantic request/response/event models)

apps/web  ─────► packages/contracts    (TypeScript types — @doc-analyst/contracts)

packages/agents ──► packages/core     (patterns, retry)
                ──► packages/tools    (tool functions)

packages/tools  ──► packages/core     (patterns, retry, embedding)

Future app ────► packages/agents      (reuse agents)
           ────► packages/core        (reuse patterns)
           ────► packages/contracts   (reuse API types)
```

---

## 4. Workspace Configuration

### 4.1 uv Workspace (Python)

```toml
# root pyproject.toml
[project]
name = "doc-analyst"
version = "0.1.0"
requires-python = ">=3.11"

[tool.uv.workspace]
members = ["packages/*", "apps/api"]
```

```toml
# apps/api/pyproject.toml
[project]
name = "doc-analyst-api"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "doc-analyst-core",
    "doc-analyst-agents",
    "doc-analyst-tools",
    "doc-analyst-contracts",
    "fastapi>=0.115",
    "uvicorn>=0.32",
    "langgraph>=0.4",
    "langgraph-supervisor>=0.0.10",
    "langgraph-checkpoint-postgres>=2.0",
    "langchain-openai>=0.3",
    "langchain-community>=0.3",
    "litellm==1.85.0",
    "instructor>=1.7",
    "tavily-python>=0.5",
    "liteparse>=1.0",
    "lancedb>=0.20",
    "tiktoken>=0.8",
    "structlog>=24.0",
    "langfuse>=2.50",
    "tenacity>=9.0",
    "pybreaker>=1.2",
    "python-dotenv>=1.0",
    "python-multipart>=0.0.12",
    "psycopg[binary]>=3.2",
]

[tool.uv.sources]
doc-analyst-core = { workspace = true }
doc-analyst-agents = { workspace = true }
doc-analyst-tools = { workspace = true }
doc-analyst-contracts = { workspace = true }
```

```toml
# packages/core/pyproject.toml
[project]
name = "doc-analyst-core"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "litellm==1.85.0",
    "tenacity>=9.0",
    "pybreaker>=1.2",
    "structlog>=24.0",
    "python-dotenv>=1.0",
]
```

```toml
# packages/agents/pyproject.toml
[project]
name = "doc-analyst-agents"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "doc-analyst-core",
    "doc-analyst-tools",
    "langgraph>=0.4",
    "langgraph-supervisor>=0.0.10",
    "langchain-openai>=0.3",
]

[tool.uv.sources]
doc-analyst-core = { workspace = true }
doc-analyst-tools = { workspace = true }
```

```toml
# packages/tools/pyproject.toml
[project]
name = "doc-analyst-tools"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "doc-analyst-core",
    "langchain-core>=0.3",
    "instructor>=1.7",
    "tavily-python>=0.5",
    "lancedb>=0.20",
    "liteparse>=1.0",
]

[tool.uv.sources]
doc-analyst-core = { workspace = true }
```

```toml
# packages/contracts/pyproject.toml
[project]
name = "doc-analyst-contracts"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = ["pydantic>=2.0"]
```

### 4.2 pnpm Workspace (JavaScript)

```yaml
# pnpm-workspace.yaml
packages:
  - "apps/web"
  - "packages/contracts"
```

```json
// packages/contracts/package.json
{
  "name": "@doc-analyst/contracts",
  "version": "0.1.0",
  "main": "src/index.ts",
  "types": "src/index.ts"
}
```

```json
// apps/web/package.json — relevant excerpt
{
  "dependencies": {
    "@doc-analyst/contracts": "workspace:*"
  }
}
```

---

## 5. Docker Compose (Local Dev)

```yaml
# docker-compose.yml
services:
  api:
    build:
      context: .
      dockerfile: apps/api/Dockerfile
    ports: ["8080:8080"]
    env_file: .env
    depends_on: [postgres]
    volumes:
      - ./packages:/workspace/packages
      - ./apps/api:/workspace/apps/api
    command: uv run uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload

  web:
    build:
      context: .
      dockerfile: apps/web/Dockerfile
    ports: ["3000:3000"]
    environment:
      - BACKEND_URL=http://api:8080
    depends_on: [api]
    volumes:
      - ./apps/web:/workspace/apps/web
      - ./packages/contracts:/workspace/packages/contracts

  postgres:
    image: postgres:17
    ports: ["5432:5432"]
    environment:
      POSTGRES_DB: langgraph_db
      POSTGRES_USER: admin
      POSTGRES_PASSWORD: admin@123
    volumes:
      - pgdata:/var/lib/postgresql/data

  langfuse:
    image: langfuse/langfuse:3
    ports: ["3001:3000"]
    depends_on: [langfuse-db, langfuse-redis, langfuse-clickhouse]
    environment:
      - DATABASE_URL=postgresql://admin:admin@123@langfuse-db:5432/langfuse
      - NEXTAUTH_SECRET=mysecret
      - SALT=mysalt
      - NEXTAUTH_URL=http://localhost:3001
      - CLICKHOUSE_URL=http://langfuse-clickhouse:8123
      - REDIS_HOST=langfuse-redis

  langfuse-db:
    image: postgres:17
    environment:
      POSTGRES_DB: langfuse
      POSTGRES_USER: admin
      POSTGRES_PASSWORD: admin@123
    volumes:
      - langfuse_pgdata:/var/lib/postgresql/data

  langfuse-redis:
    image: redis:7

  langfuse-clickhouse:
    image: clickhouse/clickhouse-server:24

volumes:
  pgdata:
  langfuse_pgdata:
```

---

## 6. Makefile

```makefile
.PHONY: dev dev-local test lint sync clean

dev:                ## Start full stack via Docker
	docker compose up -d

dev-stop:           ## Stop all containers
	docker compose down

dev-local:          ## Start without Docker (for debugging)
	@echo "Starting API..."
	cd apps/api && uv run uvicorn app.main:app --reload --port 8080 &
	@echo "Starting Web..."
	cd apps/web && pnpm dev &
	@echo "All services started. API: http://localhost:8080, Web: http://localhost:3000"

sync:               ## Install all dependencies
	uv sync
	cd apps/web && pnpm install

test:               ## Run all tests
	uv run pytest apps/api packages/
	cd apps/web && pnpm test

lint:               ## Lint everything
	uv run ruff check apps/api packages/
	cd apps/web && pnpm lint

format:             ## Format everything
	uv run ruff format apps/api packages/
	cd apps/web && pnpm format

clean:              ## Clean build artifacts
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	rm -rf apps/api/uploads apps/api/lancedb_data
```

---

## 7. Shared Contracts (Single Source of Truth)

The `packages/contracts/` package defines the API contract between frontend and backend. Both sides import from here — no duplicate type definitions.

### Python (Pydantic)

```python
# packages/contracts/contracts/events.py
from pydantic import BaseModel

class TokenEvent(BaseModel):
    event: str = "token"
    content: str
    agent: str

class AgentStartEvent(BaseModel):
    event: str = "agent_start"
    agent: str

class AgentEndEvent(BaseModel):
    event: str = "agent_end"
    agent: str

class ErrorEvent(BaseModel):
    event: str = "error"
    message: str

class DoneEvent(BaseModel):
    event: str = "done"
```

```python
# packages/contracts/contracts/requests.py
from pydantic import BaseModel

class ChatRequest(BaseModel):
    message: str
    session_id: str
    file_ids: list[str] = []

class UploadResponse(BaseModel):
    file_id: str
    filename: str
    pages: int
    status: str = "ready"

class FileMetadata(BaseModel):
    file_id: str
    filename: str
    pages: int
    size: int
```

### TypeScript (mirror)

```typescript
// packages/contracts/src/index.ts

// SSE Events
export interface TokenEvent {
  event: "token";
  content: string;
  agent: string;
}

export interface AgentStartEvent {
  event: "agent_start";
  agent: string;
}

export interface AgentEndEvent {
  event: "agent_end";
  agent: string;
}

export interface ErrorEvent {
  event: "error";
  message: string;
}

// Requests & Responses
export interface ChatRequest {
  message: string;
  session_id: string;
  file_ids: string[];
}

export interface UploadResponse {
  file_id: string;
  filename: string;
  pages: number;
  status: string;
}

export interface FileMetadata {
  file_id: string;
  filename: string;
  pages: number;
  size: number;
}
```

---

## 8. Import Path Changes

With the monorepo, import paths change from app-internal to package imports:

| Before (flat be/) | After (monorepo) |
|--------------------|------------------|
| `from app.utils.patterns import singleton` | `from core.patterns import singleton` |
| `from app.utils.retry import retryable` | `from core.retry import retryable` |
| `from app.utils.llm_context_manager import LLMContextManager` | `from core.llm_context_manager import LLMContextManager` |
| `from app.agents.registry import AgentRegistry` | `from agents.registry import AgentRegistry` |
| `from app.agents.pdf_agent import ...` | `from agents.pdf_agent import ...` |
| `from app.models.schemas import ChatRequest` | `from contracts.requests import ChatRequest` |
| `import { ChatRequest } from "@/types"` | `import { ChatRequest } from "@doc-analyst/contracts"` |

---

## 9. Git & CI

### .gitignore

```gitignore
# Python
__pycache__/
*.pyc
.venv/
uv.lock          # optional: lock or not lock, team decides

# Node
node_modules/
.next/

# Data (per-session, never committed)
apps/api/uploads/
apps/api/lancedb_data/

# Environment
.env
apps/web/.env.local

# IDE
.idea/
.vscode/
```

### CI Pipeline (future)

```
on push:
  ├── lint (ruff + eslint) — parallel
  ├── type-check (pyright + tsc) — parallel
  ├── test-packages (pytest packages/) — parallel
  ├── test-api (pytest apps/api/)
  ├── test-web (pnpm test)
  └── build (docker compose build)
```

---

## 10. Why This Structure

| Concern | How monorepo solves it |
|---------|----------------------|
| **Code reuse** | `packages/agents/` and `packages/core/` importable by any future app |
| **API contract sync** | `packages/contracts/` — one source of truth, Python + TypeScript |
| **Atomic changes** | Update agent + API + frontend in one PR |
| **Dependency consistency** | Single `uv.lock` — no version drift between packages |
| **Dev experience** | `make dev` starts everything, `make sync` installs everything |
| **Testing** | Test packages independently, test app integration separately |
| **Future apps** | Add `apps/admin-dashboard/` or `apps/batch-processor/` — reuses all packages |
