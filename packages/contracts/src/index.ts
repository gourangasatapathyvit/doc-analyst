// Shared API types — TypeScript mirror of Python Pydantic models.
// Single source of truth: keep in sync with contracts/*.py

// ---------------------------------------------------------------------------
// SSE Events (streamed from backend → frontend via proxy)
// ---------------------------------------------------------------------------
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

export interface DoneEvent {
  event: "done";
}

export type SSEEvent =
  | TokenEvent
  | AgentStartEvent
  | AgentEndEvent
  | ErrorEvent
  | DoneEvent;

// ---------------------------------------------------------------------------
// Requests & Responses
// ---------------------------------------------------------------------------
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
