# Frontend PRD — Document Analyst Web App (`apps/web`)

## 1. Overview

The Next.js frontend application within the `doc-analyst` monorepo. A production-grade chat UI that lets users upload documents, ask questions, and receive streaming responses. API routes act as a **proxy layer** — the browser never talks to FastAPI directly.

API types are imported from `@doc-analyst/contracts` (shared package in `packages/contracts/`) — single source of truth for request/response/event types between frontend and backend.

See `project.prd.md` for monorepo structure, workspace config, and shared package details.

The frontend is **domain-agnostic** — it works with any document type (insurance, legal, technical, etc.). The domain context comes from the uploaded document, not the UI. Multiple documents can be uploaded per session — the backend uses LanceDB vector search (RAG) so only relevant chunks are sent to the LLM, regardless of how many documents exist.

---

## 2. Tech Stack

| Layer           | Choice                        | Why                                                    |
|-----------------|-------------------------------|--------------------------------------------------------|
| Framework       | Next.js 15 (App Router)       | Industry standard for AI chat apps, SSR, API routes    |
| Language        | TypeScript                    | Type safety, better DX, industry standard              |
| AI Streaming    | Vercel AI SDK (`ai` package)  | `useChat` hook handles streaming, state, abort natively |
| UI Components   | shadcn/ui                     | Copy-paste components, not a dependency — you own the code |
| Styling         | Tailwind CSS v4               | Utility-first, pairs with shadcn, industry standard    |
| Icons           | Lucide React                  | Clean, consistent icon set (ships with shadcn)         |
| File Upload     | react-dropzone                | Mature drag-and-drop + click upload                    |
| Markdown        | react-markdown + remark-gfm   | Render agent responses as rich markdown                |
| Package Manager | pnpm                          | Fast, disk-efficient, workspace-friendly               |
| Node            | 20 LTS+                       |                                                        |

---

## 3. Architecture — Proxy Pattern

```
┌──────────────────────────────────────────────────────────┐
│                        Browser                            │
│         ALL requests go to Next.js (port 3000)            │
└────────────────────────┬─────────────────────────────────┘
                         │  same-origin (no CORS)
┌────────────────────────▼─────────────────────────────────┐
│                    Next.js (port 3000)                     │
│                                                           │
│  /app/page.tsx              → Chat UI (React)             │
│  /app/api/chat/route.ts     → Proxy: POST → FastAPI /api/chat  │
│  /app/api/upload/route.ts   → Proxy: POST → FastAPI /api/upload │
│  /app/api/files/[id]/route.ts → Proxy: DELETE → FastAPI   │
│                                                           │
│  Translates FastAPI SSE → Vercel AI SDK stream format     │
└────────────────────────┬─────────────────────────────────┘
                         │  internal HTTP (localhost:8080)
┌────────────────────────▼─────────────────────────────────┐
│               FastAPI Backend (port 8080)                  │
│               Never exposed to browser                    │
└──────────────────────────────────────────────────────────┘
```

**Why proxy**:
- Zero CORS configuration needed
- Backend stays internal, never exposed to browser
- Auth lives in one place (Next.js middleware) when added later
- Stream format translation (FastAPI SSE → AI SDK protocol) is clean
- Deploy as one unit — no nginx/reverse proxy needed
- This is how ChatGPT, Claude.ai, and Perplexity are built

---

## 4. Pages & Layout

### 4.1 Single-Page Chat Layout

```
┌──────────────────────────────────────────────────────────────┐
│  HEADER BAR                                                   │
│  [Logo] Document Analyst              [New Chat] [Theme]      │
├─────────────────────┬────────────────────────────────────────┤
│                     │                                        │
│  SIDEBAR (280px)    │   MAIN CHAT AREA                       │
│                     │                                        │
│  ┌───────────────┐  │   ┌──────────────────────────────────┐ │
│  │ DROP FILES    │  │   │                                  │ │
│  │ HERE          │  │   │  Welcome! Upload a document and  │ │
│  │ or click      │  │   │  ask me anything about it.       │ │
│  └───────────────┘  │   │                                  │ │
│                     │   ├──────────────────────────────────┤ │
│  FILES              │   │ User: "What are the premium      │ │
│  ┌───────────────┐  │   │  payment options?"               │ │
│  │ 📄 policy.pdf │  │   ├──────────────────────────────────┤ │
│  │ 42 pages  [x] │  │   │ [pdf_agent → analyzer_agent]     │ │
│  └───────────────┘  │   │                                  │ │
│                     │   │ The document describes three      │ │
│  AGENT ACTIVITY     │   │ premium payment options:          │ │
│  ● pdf_agent       │   │ 1. Annual payment...             │ │
│  ○ research_agent  │   │ 2. Semi-annual...                │ │
│  ○ analyzer_agent  │   │ 3. Monthly... ▌ (streaming)      │ │
│                     │   │                                  │ │
│                     │   └──────────────────────────────────┘ │
│                     │                                        │
│                     │   ┌──────────────────────────┐ [Send]  │
│                     │   │ Ask about your documents… │         │
│                     │   └──────────────────────────┘         │
└─────────────────────┴────────────────────────────────────────┘
```

### 4.2 Sidebar Components

| Component           | Implementation                              | Description                                   |
|---------------------|---------------------------------------------|-----------------------------------------------|
| File Dropzone       | `react-dropzone` + shadcn Card              | Drag-and-drop or click. Accepts PDF, DOCX, PPTX, XLSX, images. Multiple files. |
| Uploaded Files List | shadcn Card list                            | Filename, page count, size. Remove button [x] per file |
| Agent Activity      | Custom component with animated dots         | Real-time: filled circle = working, empty = idle. Updates via stream annotations |
| New Chat Button     | shadcn Button                               | Generates new session ID, clears messages and files |

### 4.3 Main Chat Area

| Component          | Implementation                               | Description                                   |
|--------------------|----------------------------------------------|-----------------------------------------------|
| Message List       | Scrollable div with auto-scroll to bottom    | User messages (right-aligned), assistant (left-aligned) |
| Assistant Message  | `react-markdown` + `remark-gfm`             | Renders markdown, tables, code blocks, lists  |
| Agent Tags         | shadcn Badge                                 | Shows agent chain: `[pdf_agent → analyzer_agent]` above each assistant message |
| Streaming Cursor   | CSS blinking cursor `▌`                      | Appended during active streaming              |
| Chat Input         | shadcn Textarea + Button                     | Auto-resize, Submit on Enter (Shift+Enter for newline), disabled during streaming |
| Empty State        | Centered prompt                              | "Upload a document and ask me anything about it" with suggested questions |

---

## 5. Features

### 5.1 Document Upload

1. User drags file onto dropzone or clicks to browse
2. Frontend shows upload progress bar (shadcn Progress)
3. `POST /api/upload` (Next.js route) proxies to FastAPI
4. On success, file appears in sidebar with metadata (name, pages, size)
5. On failure, toast notification via shadcn `Sonner`
6. User can remove file via [x] → `DELETE /api/files/{file_id}`

### 5.2 Chat with Streaming (Vercel AI SDK)

```typescript
// Core hook — handles everything
const { messages, input, handleInputChange, handleSubmit, isLoading, stop, data } = useChat({
  api: "/api/chat",           // Next.js proxy route
  body: {                     // Extra fields sent with every message
    session_id: sessionId,
    file_ids: uploadedFiles.map(f => f.file_id),
  },
  onResponse(response) {
    // Stream started — could update UI state
  },
  onFinish(message) {
    // Stream complete — message fully received
  },
  onError(error) {
    // Handle errors — show toast
  },
});
```

**What `useChat` handles automatically**:
- Message state management (user + assistant messages)
- Streaming token-by-token rendering
- Loading state (`isLoading`)
- Abort/cancel via `stop()`
- Error handling
- Request deduplication

### 5.3 Agent Activity (via Stream Annotations)

The proxy route translates FastAPI's `agent_start` / `agent_end` SSE events into Vercel AI SDK **data stream annotations**. The frontend reads these to update the sidebar:

```typescript
// Stream annotations arrive via the `data` field from useChat
// Custom hook to track active agent
function useAgentActivity(data: JSONValue[] | undefined) {
  const [activeAgent, setActiveAgent] = useState<string | null>(null);
  const [agentHistory, setAgentHistory] = useState<string[]>([]);

  useEffect(() => {
    // Parse latest data annotations for agent_start / agent_end
    // Update activeAgent and agentHistory accordingly
  }, [data]);

  return { activeAgent, agentHistory };
}
```

### 5.4 Session Management

- Session ID: UUID generated client-side, stored in `localStorage`
- Passed in `body` of every `useChat` request
- "New Chat" → new UUID, clear messages, clear files, reset agent state
- Session persists across page refreshes (messages reload from `useChat` history or localStorage)

### 5.5 Error Handling

| Scenario             | UX                                                     |
|----------------------|--------------------------------------------------------|
| Network error        | Toast: "Connection lost. Retrying..." + auto-retry     |
| Upload failure       | Toast with reason (file too large, unsupported format)  |
| Stream interruption  | Show partial response + "Response interrupted" badge    |
| Backend down         | Toast: "Service unavailable" + retry button in chat     |
| Abort by user        | `stop()` — partial response stays visible              |

---

## 6. Next.js API Routes (Proxy Layer)

### `POST /api/chat/route.ts`

The most important route. Translates between FastAPI SSE and Vercel AI SDK stream protocol.

```typescript
import { createDataStreamResponse } from "ai";

export async function POST(req: Request) {
  const body = await req.json();

  const requestId = crypto.randomUUID().slice(0, 8);

  const backendResponse = await fetch(`${BACKEND_URL}/api/chat`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-Request-ID": requestId,
      "X-Session-ID": body.session_id,
    },
    body: JSON.stringify({
      message: body.messages.at(-1)?.content,  // latest user message
      session_id: body.session_id,
      file_ids: body.file_ids,
    }),
  });

  return createDataStreamResponse({
    execute(dataStream) {
      // Read FastAPI SSE events
      // Map: token → dataStream.writeText()
      // Map: agent_start → dataStream.writeMessageAnnotation()
      // Map: agent_end → dataStream.writeMessageAnnotation()
      // Map: done → close
    },
  });
}
```

### `POST /api/upload/route.ts`

```typescript
export async function POST(req: Request) {
  const formData = await req.formData();
  const requestId = crypto.randomUUID().slice(0, 8);

  const backendResponse = await fetch(`${BACKEND_URL}/api/upload`, {
    method: "POST",
    headers: {
      "X-Request-ID": requestId,
    },
    body: formData,
  });

  return Response.json(await backendResponse.json());
}
```

### `DELETE /api/files/[id]/route.ts`

```typescript
export async function DELETE(req: Request, { params }: { params: { id: string } }) {
  const { searchParams } = new URL(req.url);
  const sessionId = searchParams.get("session_id");

  const requestId = crypto.randomUUID().slice(0, 8);

  const backendResponse = await fetch(
    `${BACKEND_URL}/api/files/${params.id}?session_id=${sessionId}`,
    {
      method: "DELETE",
      headers: { "X-Request-ID": requestId },
    }
  );

  return Response.json(await backendResponse.json());
}
```

---

## 7. State Management

React hooks + Context. No external state library needed.

```typescript
// Session context — provides session_id and file state globally
interface SessionState {
  sessionId: string;
  uploadedFiles: UploadedFile[];
  activeAgent: string | null;
  agentHistory: string[];        // agents that contributed to current response
  addFile: (file: UploadedFile) => void;
  removeFile: (fileId: string) => void;
  resetSession: () => void;
}

interface UploadedFile {
  file_id: string;
  filename: string;
  pages: number;
  size: number;
}
```

---

## 8. Non-Functional Requirements

| Requirement       | Target                                          |
|-------------------|-------------------------------------------------|
| First token       | < 2s after user sends message                   |
| File upload       | Support up to 50MB per file                     |
| Bundle size       | < 200KB first load JS (Next.js handles this)    |
| Browser support   | Chrome, Edge, Firefox (latest 2 versions)       |
| Responsiveness    | Desktop-first, usable at 1024px+. Sidebar collapses on mobile |
| Accessibility     | shadcn components are accessible by default (ARIA, keyboard nav) |
| Theme             | Light mode default. Dark mode support via shadcn theme |

---

## 9. File Structure

**Note**: API types are imported from `@doc-analyst/contracts` (see `packages/contracts/` in `project.prd.md`). No local `types/` directory needed.

```
apps/web/
├── package.json                     # depends on @doc-analyst/contracts (workspace:*)
├── pnpm-lock.yaml
├── next.config.ts
├── tsconfig.json
├── tailwind.config.ts
├── postcss.config.mjs
├── .env.local                       # BACKEND_URL=http://localhost:8080
├── components.json                  # shadcn/ui config
├── Dockerfile
│
├── app/
│   ├── layout.tsx                   # Root layout: fonts, theme provider, metadata
│   ├── page.tsx                     # Main chat page
│   ├── globals.css                  # Tailwind base + shadcn CSS variables
│   │
│   └── api/                         # Proxy routes (backend never exposed to browser)
│       ├── chat/
│       │   └── route.ts             # POST — proxy to FastAPI, translate SSE → AI SDK stream
│       ├── upload/
│       │   └── route.ts             # POST — proxy file upload to FastAPI
│       └── files/
│           └── [id]/
│               └── route.ts         # DELETE — proxy file removal to FastAPI
│
├── components/
│   ├── chat/
│   │   ├── chat-container.tsx       # Wraps useChat, provides messages + input
│   │   ├── message-list.tsx         # Renders all messages with auto-scroll
│   │   ├── message-bubble.tsx       # Single message: avatar, content, agent tags
│   │   ├── chat-input.tsx           # Textarea + send button + stop button
│   │   └── empty-state.tsx          # Welcome screen with suggested questions
│   │
│   ├── sidebar/
│   │   ├── sidebar.tsx              # Sidebar shell
│   │   ├── file-dropzone.tsx        # Drag-and-drop upload area
│   │   ├── file-list.tsx            # Uploaded files with remove button
│   │   └── agent-activity.tsx       # Real-time agent status indicators
│   │
│   └── ui/                          # shadcn/ui components (auto-generated)
│       ├── button.tsx
│       ├── card.tsx
│       ├── badge.tsx
│       ├── textarea.tsx
│       ├── progress.tsx
│       ├── sonner.tsx               # Toast notifications
│       └── ...
│
├── hooks/
│   ├── use-session.ts               # Session ID + file management
│   └── use-agent-activity.ts        # Parse stream annotations for agent status
│
└── lib/
    ├── utils.ts                     # cn() helper (shadcn standard)
    ├── logger.ts                    # Dev-only console logging
    └── constants.ts                 # App-wide constants

# Shared types imported from workspace package:
#   import type { ChatRequest, UploadResponse, FileMetadata } from "@doc-analyst/contracts"
#   import type { TokenEvent, AgentStartEvent, AgentEndEvent } from "@doc-analyst/contracts"
```

---

## 10. Dependencies

```json
{
  "dependencies": {
    "@doc-analyst/contracts": "workspace:*",
    "next": "^15.0",
    "react": "^19.0",
    "react-dom": "^19.0",
    "ai": "^4.0",
    "react-markdown": "^9.0",
    "remark-gfm": "^4.0",
    "react-dropzone": "^14.0",
    "lucide-react": "^0.400",
    "sonner": "^2.0",
    "uuid": "^10.0",
    "class-variance-authority": "^0.7",
    "clsx": "^2.0",
    "tailwind-merge": "^2.0"
  },
  "devDependencies": {
    "typescript": "^5.5",
    "@types/node": "^22.0",
    "@types/react": "^19.0",
    "tailwindcss": "^4.0",
    "@tailwindcss/postcss": "^4.0",
    "eslint": "^9.0",
    "eslint-config-next": "^15.0"
  }
}
```

---

## 11. Environment Variables

```bash
# apps/web/.env.local
BACKEND_URL=http://localhost:8080    # FastAPI backend (internal, never exposed to browser)
# When using docker-compose: BACKEND_URL=http://api:8080
```

Only one env var needed. Everything else is handled by the backend.

---

## 12. Observability (Frontend Role)

The frontend's observability responsibility is lightweight — it generates correlation IDs and forwards them to the backend, where all tracing and logging happens.

### Request Correlation

Every proxy route generates a `X-Request-ID` header and forwards it to FastAPI. This links the browser action to the full backend trace (structlog + Langfuse).

```
Browser action → Next.js proxy (generates X-Request-ID: req_8f3a)
                     │
                     ▼ headers: { X-Request-ID: req_8f3a, X-Session-ID: sess_abc }
               FastAPI middleware picks up both IDs
                     │
                     ├── structlog: all logs tagged with request_id=req_8f3a
                     └── Langfuse: trace tagged with session_id=sess_abc
```

### Console Logging (Dev Only)

```typescript
// lib/logger.ts — thin wrapper, dev only
const isDev = process.env.NODE_ENV === "development";

export function log(event: string, data?: Record<string, unknown>) {
  if (isDev) console.log(`[${event}]`, data);
}

// Usage: log("upload_started", { filename: "policy.pdf", size: 4_194_304 });
```

No production frontend logging framework needed — all meaningful tracing lives in the backend.

---

## 13. Future Enhancements (Out of Scope for v1)

- PDF page preview in sidebar (pdf.js)
- Export chat as PDF/markdown
- Multi-user auth (NextAuth.js)
- Voice input (Web Speech API)
- Code syntax highlighting in responses (rehype-highlight)
- Chat history sidebar (list of past sessions)
- Mobile-optimized responsive layout
- Keyboard shortcuts (Cmd+K for new chat, etc.)

---

*This PRD will be moved to `docs/frontend.prd.md` when the monorepo is scaffolded. See `project.prd.md` for overall architecture.*
