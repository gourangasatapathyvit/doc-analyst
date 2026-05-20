"""SSE event types streamed from the backend to the frontend."""

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
