"""Request and response models for the API."""

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
