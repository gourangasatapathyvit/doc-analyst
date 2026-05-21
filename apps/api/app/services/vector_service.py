"""Vector Service — LanceDB chunk, embed, index, search with hybrid retrieval."""

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
    """Manages per-session LanceDB indexes with hybrid search (vector + BM25)."""

    def __init__(self):
        self._embedding = AzureOpenAIEmbedding()
        self._tokenizer = tiktoken.get_encoding("cl100k_base")
        self._dbs: dict[str, Any] = {}
        self._fts_indexed: set[str] = set()  # track which sessions have FTS index

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

    def _ensure_fts_index(self, session_id: str, table) -> None:
        """Create or rebuild FTS index on the text column."""
        try:
            table.create_fts_index("text", replace=True)
            self._fts_indexed.add(session_id)
            logger.info("fts_index_created", session_id=session_id)
        except Exception as e:
            logger.warning("fts_index_failed", session_id=session_id, error=str(e))

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
            table = db.create_table(table_name, data=all_chunks)

        # Create/rebuild FTS index after adding new data
        self._ensure_fts_index(session_id, table)

        logger.info(
            "document_indexed",
            session_id=session_id,
            file_id=parsed.file_id,
            chunks=len(all_chunks),
        )
        return len(all_chunks)

    async def search(
        self,
        query: str,
        session_id: str = "",
        top_k: int = 5,
        search_mode: str = "hybrid",
    ) -> list[dict]:
        """Search documents using vector, FTS, or hybrid (RRF) mode.

        Args:
            query: Search query text
            session_id: Session to search in
            top_k: Number of results to return
            search_mode: "vector", "fts", or "hybrid" (default)
        """
        if not session_id:
            return []

        try:
            db = self._get_db(session_id)
            table = db.open_table("documents")
        except Exception:
            return []

        if search_mode == "fts":
            return self._search_fts(table, query, top_k)
        elif search_mode == "vector":
            return await self._search_vector(table, query, top_k)
        else:
            return await self._search_hybrid(table, query, top_k)

    async def _search_vector(self, table, query: str, top_k: int) -> list[dict]:
        """Semantic search via vector similarity."""
        query_vector = (await self._embedding.embed([query]))[0]
        results = table.search(query_vector).limit(top_k).to_list()

        return [
            {
                "text": r["text"],
                "filename": r["filename"],
                "page_number": r["page_number"],
                "file_id": r["file_id"],
                "score": r.get("_distance", 0.0),
                "source": "vector",
            }
            for r in results
        ]

    def _search_fts(self, table, query: str, top_k: int) -> list[dict]:
        """BM25 full-text search."""
        try:
            results = table.search(query, query_type="fts").limit(top_k).to_list()
        except Exception as e:
            logger.warning("fts_search_failed", error=str(e))
            return []

        return [
            {
                "text": r["text"],
                "filename": r["filename"],
                "page_number": r["page_number"],
                "file_id": r["file_id"],
                "score": r.get("_score", 0.0),
                "source": "fts",
            }
            for r in results
        ]

    async def _search_hybrid(self, table, query: str, top_k: int) -> list[dict]:
        """Hybrid search: vector + BM25 merged via Reciprocal Rank Fusion (RRF).

        RRF score = sum(1 / (k + rank)) across both result lists.
        This balances semantic relevance with exact keyword matches.
        """
        k = 60  # RRF constant (standard value)

        # Run both searches in parallel-ish (FTS is sync, vector is async)
        vector_results = await self._search_vector(table, query, top_k=top_k * 2)
        fts_results = self._search_fts(table, query, top_k=top_k * 2)

        # Build RRF scores keyed by chunk id
        rrf_scores: dict[str, float] = {}
        chunk_data: dict[str, dict] = {}

        for rank, r in enumerate(vector_results):
            chunk_id = r.get("file_id", "") + "_" + str(r.get("page_number", ""))
            rrf_scores[chunk_id] = rrf_scores.get(chunk_id, 0) + 1.0 / (k + rank + 1)
            chunk_data[chunk_id] = r

        for rank, r in enumerate(fts_results):
            chunk_id = r.get("file_id", "") + "_" + str(r.get("page_number", ""))
            rrf_scores[chunk_id] = rrf_scores.get(chunk_id, 0) + 1.0 / (k + rank + 1)
            if chunk_id not in chunk_data:
                chunk_data[chunk_id] = r

        # Sort by RRF score descending
        sorted_ids = sorted(rrf_scores, key=lambda cid: rrf_scores[cid], reverse=True)

        results = []
        seen_texts = set()
        for chunk_id in sorted_ids[:top_k]:
            r = chunk_data[chunk_id]
            # Deduplicate by text content
            text_key = r["text"][:100]
            if text_key in seen_texts:
                continue
            seen_texts.add(text_key)

            r["score"] = round(rrf_scores[chunk_id], 4)
            r["source"] = "hybrid"
            results.append(r)

        logger.info(
            "hybrid_search",
            query=query[:50],
            vector_hits=len(vector_results),
            fts_hits=len(fts_results),
            merged_results=len(results),
        )

        return results

    async def remove_file(self, session_id: str, file_id: str) -> None:
        try:
            db = self._get_db(session_id)
            table = db.open_table("documents")
            table.delete(f"file_id = '{file_id}'")
            # Rebuild FTS index after deletion
            self._ensure_fts_index(session_id, table)
        except Exception:
            pass
