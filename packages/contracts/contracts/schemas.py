"""Domain models shared across packages."""

from dataclasses import dataclass, field

from pydantic import BaseModel


class DocumentChunk(BaseModel):
    """A single chunk stored in LanceDB."""

    id: str
    text: str
    vector: list[float]
    file_id: str
    filename: str
    page_number: int
    chunk_index: int


@dataclass
class ParsedDocument:
    """Cached parse result for direct page access."""

    file_id: str
    filename: str
    pages: dict[int, str] = field(default_factory=dict)
    page_count: int = 0
