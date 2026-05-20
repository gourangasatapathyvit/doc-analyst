# Backend PRD — Document Analyst API (`apps/api`)

## 1. Overview

The FastAPI backend application within the `doc-analyst` monorepo. Orchestrates a multi-agent system via LangGraph Supervisor with streaming SSE responses.

This app is thin — it wires together shared packages (`packages/core`, `packages/agents`, `packages/tools`, `packages/contracts`) with FastAPI routes, middleware, and services. Agent logic, tools, design patterns, and API types live in shared packages for reuse.

See `project.prd.md` for monorepo structure, workspace config, and shared package details.

The system is **domain-agnostic** — agents work with any document type. Domain context comes from the document content, not hardcoded prompts.

---

## 2. Tech Stack

| Layer            | Choice                     | Why                                       |
|------------------|----------------------------|-------------------------------------------|
| Framework        | FastAPI                    | Async-native, SSE support, OpenAPI docs   |
| LLM Orchestration| LangGraph + langgraph-supervisor | Supervisor multi-agent with streaming |
| LLM Gateway      | litellm 1.85.0             | Unified LLM interface, model registry, cost tracking, streaming. Provider-agnostic — swap Azure for any provider with one line |
| Structured Output| instructor                 | Pydantic-validated LLM responses. Pairs with litellm for typed agent outputs |
| LLM              | Azure OpenAI (o4-mini)     | Available in .env, cost-effective         |
| PDF Parsing      | LiteParse                  | Local, fast, layout-aware, no cloud dep   |
| Vector Store     | LanceDB (local/embedded)   | Embedded, no server, per-session RAG index |
| Embeddings       | Azure OpenAI text-embedding-3-large | Already configured in .env, 3072 dims |
| Web Search       | Tavily API                 | Already configured in .env                |
| Checkpointing    | PostgreSQL (psycopg)       | Already running, conversation memory      |
| Resilience       | tenacity + pybreaker       | Retry with exponential backoff + circuit breaker for external calls |
| Package Manager  | uv                         | Fast, modern                              |
| Python           | 3.11+                      |                                           |
| Server           | Uvicorn                    | ASGI server for FastAPI                   |

---

## 3. Architecture

```
┌─────────────────────────────────────────────────────────┐
│                     FastAPI App                          │
│                                                         │
│  /api/upload    → FileService → saves to /uploads/      │
│  /api/chat      → SSE stream from LangGraph             │
│  /api/files/    → file management                       │
│  /api/health    → health check                          │
│                                                         │
│  ┌───────────────────────────────────────────────────┐  │
│  │            LangGraph Supervisor                   │  │
│  │                                                   │  │
│  │  Supervisor Agent (o4-mini)                       │  │
│  │    │                                              │  │
│  │    ├── pdf_agent ──► LanceDB (vector search)      │  │
│  │    │   Tools: search_document, get_page,          │  │
│  │    │          list_documents                       │  │
│  │    │                                              │  │
│  │    ├── research_agent                             │  │
│  │    │   Tools: tavily_search                       │  │
│  │    │                                              │  │
│  │    ├── analyzer_agent                             │  │
│  │    │   Tools: (LLM-only, no external tools)       │  │
│  │    │                                              │  │
│  │    └── [future agents via registry]               │  │
│  │                                                   │  │
│  └───────────────────────────────────────────────────┘  │
│                                                         │
│  LanceDB ←── Per-session vector index (embedded, local) │
│  PostgreSQL ←── LangGraph Checkpointer                  │
│  /uploads/  ←── Uploaded files (per session)            │
└─────────────────────────────────────────────────────────┘
```

---

## 4. API Endpoints

**Note**: These endpoints are called by the **Next.js proxy routes**, not by the browser directly. FastAPI is internal-only (localhost:8080). The Next.js frontend (localhost:3000) translates between the browser and these endpoints.

### 4.1 `POST /api/upload`

Upload a document for the current session.

- **Request**: `multipart/form-data`
  - `file`: The document file (PDF, DOCX, PPTX, XLSX, images)
  - `session_id`: UUID string (form field)
- **Response** `200`:
  ```json
  {
    "file_id": "a1b2c3",
    "filename": "whole_life_product.pdf",
    "pages": 42,
    "status": "ready"
  }
  ```
- **Processing**:
  1. Validate file type and size (max 50MB)
  2. Save to `uploads/{session_id}/{file_id}_{filename}`
  3. Parse with LiteParse to extract text and cache the result
  4. Return metadata

### 4.2 `POST /api/chat`

Send a message and receive a streaming response.

- **Request body**:
  ```json
  {
    "message": "What are the premium payment options?",
    "session_id": "uuid-string",
    "file_ids": ["a1b2c3"]
  }
  ```
- **Response**: `text/event-stream` (SSE)
- **SSE Events**:

  | Event          | Data                                      | When                          |
  |----------------|-------------------------------------------|-------------------------------|
  | `agent_start`  | `{"agent": "pdf_agent"}`                  | Supervisor hands off to agent |
  | `token`        | `{"content": "The ", "agent": "pdf_agent"}`| Each streamed token           |
  | `agent_end`    | `{"agent": "pdf_agent"}`                  | Agent completes its turn      |
  | `error`        | `{"message": "error details"}`            | On failure                    |
  | `done`         | `{}`                                      | Stream complete               |

- **Processing**:
  1. Load session checkpoint from PostgreSQL
  2. Inject uploaded file context into state
  3. Run supervisor graph with streaming
  4. Yield SSE events as tokens are generated
  5. Save checkpoint after completion

### 4.3 `DELETE /api/files/{file_id}`

Remove an uploaded file from the session.

- **Query param**: `session_id`
- **Response** `200`: `{ "status": "deleted" }`

### 4.4 `GET /api/health`

- **Response** `200`: `{ "status": "ok" }`

---

## 5. Agents

### 5.1 Supervisor Agent

The top-level orchestrator. Does NOT answer questions directly — it routes to specialist agents.

```python
SUPERVISOR_PROMPT = """You are a document analyst assistant that coordinates specialist agents.

Available agents:
{agent_descriptions}

Instructions:
- Route user queries to the most appropriate agent(s)
- For questions about uploaded documents, start with pdf_agent
- For questions needing external context, use research_agent  
- For synthesis, comparison, or explanation, use analyzer_agent
- You may chain agents: e.g. pdf_agent → analyzer_agent
- Always provide a complete answer — don't leave partial responses

The user has uploaded these files: {file_context}
"""
```

- **Model**: Azure OpenAI o4-mini
- **Output mode**: `full_history` (agents see prior conversation)

### 5.2 PDF Agent (`pdf_agent`)

Specialist for document retrieval via RAG. Does NOT receive full document text — instead queries the LanceDB vector index to retrieve only relevant chunks.

**Prompt**:
```
You are a document retrieval specialist. Use your tools to search 
and retrieve information from uploaded documents.
Always cite the page number and source filename when referencing content.
Do NOT try to read entire documents — use search_document to find relevant sections.
Use get_page only when you need the exact full text of a specific page.
```

**Tools**:

#### `search_document(query: str, top_k: int = 5) -> str`
Semantic search over all uploaded documents via LanceDB vector index.
- Embeds the query using Azure OpenAI text-embedding-3-large
- Searches the session's LanceDB table
- Returns top_k most relevant chunks with metadata (page number, filename, relevance score)
- This is the primary tool — use it first for any document question

#### `get_page(filename: str, page_number: int) -> str`
Get the full text of a specific page from a specific document.
- Used when the agent needs exact content after identifying the right page via search
- Reads from the parse cache (not LanceDB)

#### `list_documents() -> str`
List all documents uploaded in the current session.
- Returns filename, page count, and file size for each document
- Useful when the agent needs to know what's available

### 5.3 Research Agent (`research_agent`)

Specialist for web research.

**Prompt**:
```
You are a web research specialist. Use Tavily search to find 
relevant external information. Always cite your sources with URLs.
```

**Tools**:

#### `tavily_search(query: str, max_results: int = 5) -> str`
Search the web using Tavily API. Returns titles, URLs, and content snippets.

### 5.4 Analyzer Agent (`analyzer_agent`)

Specialist for synthesis and reasoning. Has no external tools — uses pure LLM reasoning over the conversation context.

**Prompt**:
```
You are an analysis specialist. Synthesize information from the 
conversation to provide clear comparisons, explanations, and summaries.
When explaining technical terms, use simple language.
Structure your responses with clear headings and bullet points.
```

**Tools**: None (LLM-only reasoning agent)

---

## 6. Agent Registry

A pluggable system for registering new agents without modifying core code.

```python
class AgentRegistry:
    """Register and manage agents for the supervisor."""
    
    def register(self, agent, description: str) -> None:
        """Add an agent to the registry."""
        
    def unregister(self, name: str) -> None:
        """Remove an agent from the registry."""
    
    def get_agents(self) -> list:
        """Return all registered agents."""
    
    def get_descriptions(self) -> str:
        """Return formatted descriptions for the supervisor prompt."""
```

**Adding a new agent in the future**:
```python
# 1. Define tools
@tool
def calculate_premium(age: int, coverage: float) -> str:
    """Calculate estimated premium."""
    ...

# 2. Create agent
math_agent = create_react_agent(
    model=llm, tools=[calculate_premium], name="math_agent"
)

# 3. Register
registry.register(math_agent, "Performs mathematical calculations and projections")

# Supervisor automatically includes it on next graph compilation
```

---

## 7. Document Ingestion Pipeline (Upload → RAG Index)

### Overview

When a user uploads a PDF, it goes through a pipeline: **parse → chunk → embed → index**. The agent never sees the full document text — it queries the vector index.

```
User uploads PDF
    │
    ▼
① LiteParse parses → spatial text per page
    │
    ▼
② Chunker splits pages into ~500-token chunks with overlap
    │
    ▼
③ Azure OpenAI embeds each chunk (text-embedding-3-large, 3072 dims)
    │
    ▼
④ LanceDB stores chunks + embeddings in session table
    │
    ▼
⑤ pdf_agent queries LanceDB (top-K retrieval) → only relevant chunks go to LLM
```

### Upload Storage

```
uploads/
└── {session_id}/
    ├── {file_id}_document1.pdf
    └── {file_id}_document2.pdf
```

### LanceDB Storage

```
lancedb_data/
└── {session_id}/          # One LanceDB database per session
    └── documents.lance/   # Single table with all chunks from all uploaded docs
```

### LanceDB Table Schema

```python
import lancedb
from pydantic import BaseModel

class DocumentChunk(BaseModel):
    id: str                  # "{file_id}_{page}_{chunk_idx}"
    text: str                # Chunk text (~500 tokens)
    vector: list[float]      # 3072-dim embedding from Azure OpenAI
    file_id: str             # Source file ID
    filename: str            # Original filename
    page_number: int         # Source page number
    chunk_index: int         # Chunk position within page
```

### Chunking Strategy

```python
# Split each page's text into overlapping chunks
CHUNK_SIZE = 500       # tokens
CHUNK_OVERLAP = 50     # tokens overlap between consecutive chunks

# Each chunk carries metadata: file_id, filename, page_number, chunk_index
# This allows the agent to cite sources precisely
```

### Embedding

Uses the Azure OpenAI embedding endpoint already in `.env`:
- Model: `text-embedding-3-large`
- Dimensions: 3072
- Endpoint: `EMBEDDING_ENDPOINT`
- API Key: `EMBEDDING_API_KEY`

Custom LanceDB embedding function wraps the Azure OpenAI client (no native Azure support in LanceDB — we register a custom `AzureOpenAIEmbeddings` function).

### Session Lifecycle

```python
# On upload: create/append to session's LanceDB table
db = lancedb.connect(f"lancedb_data/{session_id}")
table = db.create_table("documents", data=chunks)   # first upload
table.add(new_chunks)                                # subsequent uploads

# On search: query the table
results = table.search(query_embedding).limit(top_k).to_pandas()

# On file delete: remove chunks by file_id
table.delete(f"file_id = '{file_id}'")

# On session end / cleanup: delete the session directory
shutil.rmtree(f"lancedb_data/{session_id}")
```

### Parse Cache (for `get_page` tool)

Page-level text is still cached in memory for direct page access:

```python
parse_cache: dict[str, ParsedDocument] = {}

@dataclass
class ParsedDocument:
    file_id: str
    filename: str
    pages: dict[int, str]       # Page number → page text
    page_count: int
```

---

## 8. Streaming Implementation

### SSE via FastAPI

```python
@app.post("/api/chat")
async def chat(request: ChatRequest):
    return StreamingResponse(
        stream_agent_response(request),
        media_type="text/event-stream"
    )

async def stream_agent_response(request: ChatRequest):
    config = {"configurable": {"thread_id": request.session_id}}
    
    async for event in supervisor_graph.astream_events(
        {"messages": [HumanMessage(content=request.message)]},
        config=config,
        version="v2"
    ):
        # Map LangGraph events to our SSE format
        if event["event"] == "on_chat_model_stream":
            chunk = event["data"]["chunk"]
            yield f"event: token\ndata: {json.dumps({...})}\n\n"
        elif event["event"] == "on_chain_start":
            yield f"event: agent_start\ndata: {json.dumps({...})}\n\n"
        ...
    
    yield "event: done\ndata: {}\n\n"
```

---

## 9. Configuration

All config from environment variables (`.env` file in project root):

| Variable | Source | Usage |
|----------|--------|-------|
| `AZURE_OPENAI_API_KEY` | .env | LLM authentication |
| `AZURE_OPENAI_ENDPOINT` | .env | LLM endpoint |
| `AZURE_OPENAI_DEPLOYMENT_NAME` | .env | Model deployment (o4-mini) |
| `AZURE_OPENAI_API_VERSION` | .env | API version |
| `TAVILY_API_KEY` | .env | Web search |
| `DB_HOST`, `DB_PORT`, `DB_USERNAME`, `DB_PASSWORD` | .env | PostgreSQL checkpointer |
| `LANGGRAPH_CHECKPOINT_DB` | .env | Checkpoint database name |
| `UVICORN_HOST`, `UVICORN_PORT` | .env | Server bind |
| `CORS_ALLOWED_ORIGINS` | .env | CORS whitelist |
| `EMBEDDING_ENDPOINT` | .env | Azure OpenAI embedding endpoint |
| `EMBEDDING_API_KEY` | .env | Embedding API key |
| `EMBEDDING_DIMENSIONS` | .env | Embedding dimensions (3072) |
| `UPLOAD_DIR` | default: `./uploads` | File storage path |
| `LANCEDB_DIR` | default: `./lancedb_data` | LanceDB storage path |
| `CHUNK_SIZE` | default: `500` | Tokens per chunk |
| `CHUNK_OVERLAP` | default: `50` | Token overlap between chunks |
| `MAX_UPLOAD_SIZE_MB` | default: `50` | Upload size limit |
| `LANGFUSE_PUBLIC_KEY` | .env | Langfuse project public key |
| `LANGFUSE_SECRET_KEY` | .env | Langfuse project secret key |
| `LANGFUSE_HOST` | default: `http://localhost:3001` | Langfuse server URL |
| `LOG_LEVEL` | default: `info` | structlog log level |
| `ENV` | default: `dev` | `dev` = console logs, `prod` = JSON logs |

---

## 10. Observability

### 10.1 Two-Layer Strategy

| Layer | Tool | What it traces | Scope |
|-------|------|----------------|-------|
| **App Logging** | structlog | HTTP requests, errors, latency, file ops, DB calls | Everything outside the LLM |
| **LLM Tracing** | Langfuse (self-hosted) | Agent routing, tool calls, token usage, cost, LLM I/O | Everything inside the LLM pipeline |

These are separate concerns. structlog traces your Python code. Langfuse traces the AI pipeline. Together they cover everything.

### 10.2 Application Logging — structlog

**Why structlog**: Outputs structured JSON (queryable), supports bound loggers (context carries automatically), processor pipeline (dev = colored console, prod = JSON), and is OTel-ready for future adoption.

**Correlation ID pattern** — every request gets a `request_id`, every log line carries it:

```python
import structlog
from contextvars import ContextVar

request_id_ctx: ContextVar[str] = ContextVar("request_id", default="")

@app.middleware("http")
async def logging_middleware(request, call_next):
    rid = request.headers.get("X-Request-ID", str(uuid.uuid4())[:8])
    request_id_ctx.set(rid)
    structlog.contextvars.bind_contextvars(
        request_id=rid,
        session_id=request.headers.get("X-Session-ID", ""),
    )
    logger.info("request_started", method=request.method, path=request.url.path)
    response = await call_next(request)
    logger.info("request_completed", status=response.status_code)
    structlog.contextvars.unbind_contextvars("request_id", "session_id")
    return response
```

**Output — dev** (colored, human-readable):
```
2026-05-20 10:23:45 [info] file_uploaded  request_id=req_8f3a session_id=sess_abc filename=policy.pdf pages=42
```

**Output — prod** (JSON, machine-parseable):
```json
{"event":"file_uploaded","request_id":"req_8f3a","session_id":"sess_abc","filename":"policy.pdf","pages":42,"timestamp":"2026-05-20T10:23:45.123Z","level":"info"}
```

**Configuration**:

```python
# app/logging_config.py
import structlog

def setup_logging(env: str = "dev"):
    renderer = (
        structlog.dev.ConsoleRenderer() if env == "dev"
        else structlog.processors.JSONRenderer()
    )
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            renderer,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
    )
```

**What gets logged**:

| Event | Fields | When |
|-------|--------|------|
| `request_started` | method, path, request_id | Every HTTP request |
| `request_completed` | status, duration_ms | Every HTTP response |
| `file_uploaded` | filename, pages, size, duration_ms | After upload + parse |
| `file_deleted` | file_id, filename | On file removal |
| `vector_index_created` | file_id, chunks_count, duration_ms | After chunking + embedding |
| `vector_search` | query, top_k, results_count, duration_ms | On pdf_agent search |
| `supervisor_start` | message_preview, file_count | Chat request begins |
| `agent_handoff` | from_agent, to_agent | Supervisor routes |
| `chat_completed` | total_tokens, total_duration_ms, agents_used | Chat request ends |
| `error` | error_type, message, traceback | Any unhandled error |

### 10.3 LLM Tracing — Langfuse (self-hosted)

**Setup** — 3 lines added to the LangGraph invocation:

```python
from langfuse.callback import CallbackHandler

langfuse_handler = CallbackHandler(
    public_key=settings.LANGFUSE_PUBLIC_KEY,
    secret_key=settings.LANGFUSE_SECRET_KEY,
    host=settings.LANGFUSE_HOST,
)

# Pass as callback — every LangGraph node is traced automatically
result = await supervisor_graph.ainvoke(
    {"messages": [HumanMessage(content=message)]},
    config={
        "configurable": {"thread_id": session_id},
        "callbacks": [langfuse_handler],
    }
)
```

**What Langfuse captures automatically**:
- Full trace tree: supervisor → agent handoffs → tool calls → LLM responses
- Per-node: latency, input/output tokens, cost
- Per-session: total cost, conversation flow
- Prompt versions (when using Langfuse prompt management)

**Langfuse self-hosted deployment** (docker-compose):

```
langfuse-web      :3001   ← Dashboard UI + API
langfuse-worker           ← Background processing
ClickHouse                ← Trace analytics (OLAP)
Redis                     ← Queue + cache
PostgreSQL                ← Metadata
MinIO                     ← Object storage
```

### 10.4 Future: OpenTelemetry (v3)

Both structlog and Langfuse are **OTel-ready**. When the project goes multi-service, OTel can be adopted without code changes — just add the OTel Collector + backend (Jaeger/Tempo + Prometheus/Grafana). For v1 (single service), correlation IDs + structlog + Langfuse cover everything OTel would, without the infrastructure overhead.

---

## 11. LLM Integration — litellm + instructor

### 11.1 litellm — Unified LLM Gateway

All LLM calls go through litellm. No direct Azure OpenAI SDK usage anywhere.

```python
import litellm

# Streaming completion — used by LangGraph agents
response = await litellm.acompletion(
    model="azure/o4-mini",
    messages=[{"role": "user", "content": "..."}],
    api_key=settings.AZURE_OPENAI_API_KEY,
    api_base=settings.AZURE_OPENAI_ENDPOINT,
    api_version=settings.AZURE_OPENAI_API_VERSION,
    stream=True,
)

# Embeddings — used by VectorService
embedding = await litellm.aembedding(
    model="azure/text-embedding-3-large",
    input=["chunk text here"],
    api_key=settings.EMBEDDING_API_KEY,
    api_base=settings.EMBEDDING_ENDPOINT,
    dimensions=3072,
)
```

**Why litellm over raw SDK**:
- Provider-agnostic — swap Azure for Anthropic/local with one config change
- Built-in model registry — `litellm.get_model_info()` for context window detection (used by LLMContextManager)
- Cost tracking — `litellm.completion_cost()` per call
- Consistent streaming interface across providers

### 11.2 instructor — Structured LLM Outputs

For agent tools that need structured, validated responses:

```python
import instructor
import litellm
from pydantic import BaseModel

client = instructor.from_litellm(litellm.acompletion)

class DocumentFacts(BaseModel):
    facts: list[str]
    page_references: list[int]
    confidence: float

result = await client.create(
    model="azure/o4-mini",
    response_model=DocumentFacts,
    messages=[{"role": "user", "content": f"Extract key facts from:\n{chunk_text}"}],
)
# result.facts → typed, validated, structured
```

**Where instructor is used**:

| Agent | Structured Output Model | Purpose |
|-------|------------------------|---------|
| pdf_agent | `SearchResults(chunks: list[ChunkResult], total_found: int)` | Structured search results with scores |
| research_agent | `WebResearch(findings: list[Finding], sources: list[str])` | Structured web research with citations |
| analyzer_agent | `Analysis(summary: str, key_points: list[str], comparison: dict)` | Structured analysis output |
| supervisor | Handled by langgraph-supervisor (tool-calling based routing) | N/A |

### 11.3 LLMContextManager — Token Budget Management

Reused from existing codebase (`@singleton` pattern). Manages context window detection and token budgets:

```python
from core.patterns import singleton

@singleton
class LLMContextManager:
    """Auto-detects model context limits via litellm. Caches per deployment."""

    def get_usable_tokens(self, deployment_name: str, fill_pct: float = 0.5) -> int:
        """Returns max_input_tokens × fill_pct."""

    def get_usable_output_tokens(self, deployment_name: str) -> int:
        """Returns safe output token budget (80% of max, minus 10% overhead)."""
```

**Used by**:
- `VectorService` — dynamic chunk sizing based on model context
- `pdf_agent` — limits how many chunks to retrieve (stays within token budget)
- `analyzer_agent` — caps synthesis output length

---

## 12. Design Patterns

### 12.1 Singleton (`@singleton` decorator)

Thread-safe singleton via double-checked locking. Applied to services that maintain state/cache:

```python
from core.patterns import singleton

@singleton
class VectorService:       # One LanceDB connection manager per process
    ...

@singleton
class ParseService:        # One parse cache per process
    ...

@singleton
class LLMContextManager:   # One model info cache per process
    ...

@singleton
class AgentRegistry:       # One agent registry per process
    ...
```

### 12.2 Retry + Circuit Breaker (`@retryable` decorator)

Exponential backoff with jitter (tenacity) + circuit breaker (pybreaker) for external calls:

```python
from core.retry import retryable, azure_ai_breaker, tavily_breaker

# Azure OpenAI — retry transient failures, circuit-break on sustained outage
@retryable(label="llm_completion", breaker=azure_ai_breaker)
async def get_completion(messages: list, model: str = "azure/o4-mini"):
    return await litellm.acompletion(model=model, messages=messages)

# Embeddings — same pattern
@retryable(label="embedding", breaker=azure_ai_breaker)
async def get_embedding(text: str):
    return await litellm.aembedding(model="azure/text-embedding-3-large", input=[text])

# Tavily — separate breaker (different service, different failure domain)
@retryable(label="tavily_search", breaker=tavily_breaker)
async def search_web(query: str):
    return await tavily_client.search(query)
```

**Circuit breakers** — one per external service:

| Breaker | Service | Trips after | Reset after |
|---------|---------|-------------|-------------|
| `azure_ai_breaker` | Azure OpenAI (LLM + embeddings) | 20 consecutive transient failures | 60s |
| `tavily_breaker` | Tavily web search | 20 consecutive transient failures | 60s |
| `db_breaker` | PostgreSQL (checkpointing) | 20 consecutive transient failures | 60s |

### 12.3 Repository Pattern

Clean separation between storage logic and business logic:

```python
class FileRepository:
    """Handles file storage, retrieval, and cleanup."""

    async def save(self, session_id: str, file: UploadFile) -> FileMetadata: ...
    async def get(self, file_id: str) -> Path: ...
    async def delete(self, file_id: str) -> None: ...
    async def list_session(self, session_id: str) -> list[FileMetadata]: ...
    async def cleanup_session(self, session_id: str) -> None: ...
```

### 12.4 Strategy Pattern (Embeddings)

Swap embedding providers without changing vector service:

```python
class EmbeddingStrategy(Protocol):
    async def embed(self, texts: list[str]) -> list[list[float]]: ...
    @property
    def dimensions(self) -> int: ...

class AzureOpenAIEmbedding(EmbeddingStrategy):
    """Azure OpenAI text-embedding-3-large via litellm."""
    async def embed(self, texts: list[str]) -> list[list[float]]:
        response = await litellm.aembedding(model="azure/text-embedding-3-large", input=texts)
        return [r["embedding"] for r in response.data]
    @property
    def dimensions(self) -> int:
        return 3072

# VectorService depends on the protocol, not the implementation
@singleton
class VectorService:
    def __init__(self, embedding: EmbeddingStrategy = AzureOpenAIEmbedding()):
        self.embedding = embedding
```

### 12.5 Factory Pattern (Agent Creation)

Standardized agent creation with consistent config:

```python
class AgentFactory:
    """Creates agents with consistent model, retry, and observability config."""

    @staticmethod
    def create(
        name: str,
        tools: list,
        prompt: str,
        model: str = "azure/o4-mini",
    ) -> CompiledGraph:
        llm = ChatLiteLLM(model=model, ...)
        return create_react_agent(
            model=llm,
            tools=tools,
            name=name,
            prompt=prompt,
        )
```

---

## 13. Error Handling

| Scenario | Behavior |
|----------|----------|
| LLM API error (transient) | `@retryable` retries up to 5× with exponential backoff. Circuit breaker opens after 20 consecutive failures |
| LLM API error (permanent) | 400/401/404 — no retry, immediate SSE `error` event |
| File parse failure | Return 422 with reason (corrupt file, unsupported format) |
| File not found | Return 404 |
| Agent timeout | 120s per agent turn, then force return partial result |
| DB connection lost | Graceful degradation — continue without checkpointing, log warning |
| Circuit breaker open | Immediate fail with "Service temporarily unavailable", no retry attempts wasted |
| Embedding failure | Retry via `@retryable`, fall back to error on upload if sustained |

---

## 14. File Structure

**Note**: Agents, tools, design patterns, and API contracts live in `packages/` (see `project.prd.md`). This app only contains FastAPI-specific code: routes, middleware, services, and config.

```
apps/api/
├── pyproject.toml              # uv workspace member, depends on packages/*
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI app, CORS, lifespan, startup (register agents)
│   ├── config.py               # Settings from .env
│   ├── logging_config.py       # structlog setup (dev console / prod JSON)
│   ├── middleware/
│   │   ├── __init__.py
│   │   └── request_context.py  # Correlation ID + structlog context binding
│   ├── api/
│   │   ├── __init__.py
│   │   ├── routes_chat.py      # POST /api/chat (SSE streaming)
│   │   ├── routes_upload.py    # POST /api/upload, DELETE /api/files
│   │   └── routes_health.py    # GET /api/health
│   └── services/
│       ├── __init__.py
│       ├── file_service.py     # FileRepository — upload, delete, path management
│       ├── parse_service.py    # @singleton ParseService — LiteParse wrapper + cache
│       ├── vector_service.py   # @singleton VectorService — LanceDB: chunk, embed, index, search
│       └── checkpoint.py       # PostgreSQL checkpointer setup
├── uploads/                    # Uploaded files (gitignored)
├── lancedb_data/               # LanceDB session indexes (gitignored)
└── Dockerfile

# Shared packages (imported, not duplicated):
#   from core.patterns import singleton
#   from core.retry import retryable, azure_ai_breaker
#   from core.llm_context_manager import LLMContextManager
#   from core.embedding import AzureOpenAIEmbedding
#   from agents.supervisor import build_supervisor
#   from agents.registry import AgentRegistry
#   from tools.pdf_tools import search_document, get_page
#   from tools.web_tools import tavily_search
#   from contracts.requests import ChatRequest, UploadResponse
#   from contracts.events import TokenEvent, AgentStartEvent
```

---

## 15. Dependencies

Dependencies are split across the monorepo. Each package declares its own deps; the root `uv.lock` resolves them together. See `project.prd.md` section 4 for full pyproject.toml listings.

**apps/api** (app-specific only — shared deps come from packages):
```
fastapi >= 0.115
uvicorn >= 0.32
langfuse >= 2.50
python-multipart >= 0.0.12
psycopg[binary] >= 3.2
# + workspace deps: doc-analyst-core, doc-analyst-agents, doc-analyst-tools, doc-analyst-contracts
```

**packages/core**: `litellm==1.85.0`, `tenacity`, `pybreaker`, `structlog`, `python-dotenv`
**packages/agents**: `langgraph`, `langgraph-supervisor`, `langchain-openai`
**packages/tools**: `instructor`, `tavily-python`, `lancedb`, `liteparse`, `langchain-core`
**packages/contracts**: `pydantic`

---

## 16. Roadmap

### v1 — Core (Current Scope)

Everything in sections 1–15 above. Manual prompts, LangGraph supervisor, streaming, 3 agents, litellm + instructor, design patterns (@singleton, @retryable, repository, strategy, factory), structlog + Langfuse observability.

### v2 — DSPy Prompt Optimization

**Goal**: Replace hand-written agent prompts with DSPy-compiled, auto-optimized signatures that measurably improve output quality.

**Why DSPy**: Manual prompts are fragile — small wording changes cause unpredictable quality shifts. DSPy treats prompts as code: you define input/output signatures and a quality metric, and DSPy compiles them into optimized prompts automatically (benchmarks show 10-40% improvement on structured tasks).

**What Changes**:

```
v1:  LangGraph node  →  raw prompt string  →  LLM
v2:  LangGraph node  →  DSPy signature      →  compiled prompt  →  LLM
```

**Signatures to Optimize**:

| Agent | DSPy Signature | Inputs → Outputs |
|-------|---------------|-------------------|
| pdf_agent | `DocumentExtract` | `(document_text, question) → (answer, page_refs, confidence)` |
| pdf_agent | `DocumentSearch` | `(query, document_text) → (relevant_sections[], relevance_scores[])` |
| research_agent | `QueryReformulate` | `(user_question, context) → (search_queries[])` |
| research_agent | `SourceSynthesize` | `(search_results[], question) → (summary, source_urls[])` |
| analyzer_agent | `CompareAnalyze` | `(facts_a, facts_b) → (comparison, pros[], cons[], verdict)` |
| analyzer_agent | `SimplifyExplain` | `(technical_text, audience_level) → (plain_explanation)` |
| supervisor | `RouteDecision` | `(user_message, agent_descriptions, file_context) → (agent_name, reasoning)` |

**Optimization Approach**:

1. **Collect evaluation data** — Log Q&A pairs from v1 usage, manually label quality (good/bad/partial)
2. **Define metrics** — Per-signature quality metrics:
   - Extraction: factual accuracy vs source document (LLM-as-judge)
   - Search: recall of relevant sections
   - Analysis: completeness + coherence score
   - Routing: correct agent selection rate
3. **Optimize** — Use DSPy optimizers:
   - `BootstrapFewShot` — auto-generate few-shot examples from training data
   - `MIPROv2` — instruction + example optimization together
4. **Evaluate** — Compare v1 (manual) vs v2 (DSPy) on held-out test set
5. **Deploy** — Swap compiled prompts into LangGraph agents

**File Structure Additions**:

```
packages/agents/agents/
├── dspy_signatures/
│   ├── __init__.py
│   ├── document.py         # DocumentExtract, DocumentSearch
│   ├── research.py         # QueryReformulate, SourceSynthesize
│   ├── analysis.py         # CompareAnalyze, SimplifyExplain
│   └── routing.py          # RouteDecision
├── dspy_optimization/
│   ├── __init__.py
│   ├── metrics.py          # Quality metric functions
│   ├── datasets.py         # Training/eval data loaders
│   └── optimize.py         # Optimization scripts
└── dspy_compiled/           # Saved optimized prompts (JSON)
    ├── document_extract.json
    ├── query_reformulate.json
    └── ...
```

**New Dependencies** (v2 only):

```
dspy >= 2.6
```

**Prerequisites before starting v2**:
- v1 is stable and deployed
- At least 50-100 labeled Q&A pairs collected from v1 usage
- Quality metrics defined and baseline measured

---

### v3 — OpenTelemetry + Production Hardening

- **OpenTelemetry adoption** — OTel Collector + Jaeger/Tempo for distributed tracing, Prometheus + Grafana for metrics. structlog and Langfuse already OTel-ready, no app code changes needed.
- Authentication / multi-user support
- Rate limiting per session
- Vector store for large document search (Azure AI Search)
- Webhook notifications
- File format conversion previews
- Long-term memory store (cross-session knowledge)

---

*This PRD will be moved to `docs/backend.prd.md` when the monorepo is scaffolded. See `project.prd.md` for overall architecture.*
