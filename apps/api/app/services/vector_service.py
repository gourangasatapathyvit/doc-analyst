"""Vector Service — LanceDB chunk, embed, index, search."""

from __future__ import annotations

from typing import Any

import lancedb
import structlog
import tiktoken

from contracts.requests import FileMetadata
from contracts.schemas import ParsedDocument
from core.embedding import AzureOpenAIEmbedding
from core.patterns import singleton

from app.config import settings

logger = structlog.get_logger()


@singleton
class VectorService:
    """Manages per-session LanceDB indexes for RAG."""

    def __init__(self):
        self._embedding = AzureOpenAIEmbedding()
        self._tokenizer = tiktoken.get_encoding("cl100k_base")
        self._dbs: dict[str, Any] = {}

    def _get_db(self, session_id: str):
        if session_id not in self._dbs:
            db_path = settings.lancedb_dir / session_id
            db_path.mkdir(parents=True, exist_ok=True)
            self._dbs[session_id] = lancedb.connect(str(db_path))
        return self._dbs[session_id]

    def _chunk_text(self, text: str, page_number: int, file_id: str, filename: str) -> list[dict]:
        tokens = self._tokenizer.encode(text)
        chunks = []
        chunk_size = settings.chunk_size
        overlap = settings.chunk_overlap
        idx = 0
        start = 0

        while start < len(tokens):
            end = min(start + chunk_size, len(tokens))
            chunk_tokens = tokens[start:end]
            chunk_text = self._tokenizer.decode(chunk_tokens)

            chunks.append({
                "id": f"{file_id}_{page_number}_{idx}",
                "text": chunk_text,
                "file_id": file_id,
                "filename": filename,
                "page_number": page_number,
                "chunk_index": idx,
            })
            idx += 1
            start += chunk_size - overlap

        return chunks

    async def index_document(
        self,
        session_id: str,
        parsed: ParsedDocument,
        metadata: FileMetadata,
    ) -> int:
        all_chunks = []
        for page_num, page_text in parsed.pages.items():
            if not page_text.strip():
                continue
            chunks = self._chunk_text(page_text, page_num, parsed.file_id, parsed.filename)
            all_chunks.extend(chunks)

        if not all_chunks:
            return 0

        texts = [c["text"] for c in all_chunks]
        vectors = await self._embedding.embed(texts)

        for chunk, vector in zip(all_chunks, vectors):
            chunk["vector"] = vector

        db = self._get_db(session_id)
        table_name = "documents"

        try:
            table = db.open_table(table_name)
            table.add(all_chunks)
        except Exception:
            db.create_table(table_name, data=all_chunks)

        logger.info(
            "vector_index_created",
            session_id=session_id,
            file_id=parsed.file_id,
            chunks=len(all_chunks),
        )
        return len(all_chunks)

    async def search(self, query: str, session_id: str = "", top_k: int = 5) -> list[dict]:
        if not session_id:
            return []

        try:
            db = self._get_db(session_id)
            table = db.open_table("documents")
        except Exception:
            return []

        query_vector = (await self._embedding.embed([query]))[0]
        results = table.search(query_vector).limit(top_k).to_list()

        return [
            {
                "text": r["text"],
                "filename": r["filename"],
                "page_number": r["page_number"],
                "file_id": r["file_id"],
                "score": r.get("_distance", 0.0),
            }
            for r in results
        ]

    async def remove_file(self, session_id: str, file_id: str) -> None:
        try:
            db = self._get_db(session_id)
            table = db.open_table("documents")
            table.delete(f"file_id = '{file_id}'")
        except Exception:
            pass
