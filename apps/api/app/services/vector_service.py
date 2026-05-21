"""Vector Service — LlamaIndex-powered RAG with LanceDB + hybrid search.

Replaces manual chunking, embedding, and search with LlamaIndex's
VectorStoreIndex, SentenceSplitter, and LanceDBVectorStore.
"""

from __future__ import annotations

from typing import Any

import structlog
from llama_index.core import StorageContext, VectorStoreIndex
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core.schema import Document, TextNode
from llama_index.embeddings.azure_openai import AzureOpenAIEmbedding
from llama_index.vector_stores.lancedb import LanceDBVectorStore

from contracts.requests import FileMetadata
from contracts.schemas import ParsedDocument
from core.patterns import singleton

from app.config import settings

logger = structlog.get_logger()


def _make_embed_model() -> AzureOpenAIEmbedding:
    """Create Azure OpenAI embedding model for LlamaIndex."""
    return AzureOpenAIEmbedding(
        model="text-embedding-3-large",
        azure_deployment=settings.embedding_deployment_name,
        api_key=settings.embedding_api_key,
        azure_endpoint=settings.azure_openai_endpoint,
        api_version=settings.embedding_api_version,
        dimensions=settings.embedding_dimensions,
    )


@singleton
class VectorService:
    """Manages per-session LlamaIndex indexes backed by LanceDB with hybrid search."""

    def __init__(self) -> None:
        self._embed_model = _make_embed_model()
        self._splitter = SentenceSplitter(
            chunk_size=settings.chunk_size,
            chunk_overlap=settings.chunk_overlap,
        )
        self._indexes: dict[str, VectorStoreIndex] = {}
        self._vector_stores: dict[str, LanceDBVectorStore] = {}

    def _get_or_create_index(self, session_id: str) -> VectorStoreIndex:
        """Get existing index or create an empty one for the session."""
        if session_id in self._indexes:
            return self._indexes[session_id]

        db_path = settings.lancedb_dir / session_id
        db_path.mkdir(parents=True, exist_ok=True)

        vector_store = LanceDBVectorStore(
            uri=str(db_path),
            table_name="documents",
            query_type="hybrid",
        )
        self._vector_stores[session_id] = vector_store

        storage_context = StorageContext.from_defaults(vector_store=vector_store)

        try:
            # Try to load existing index
            index = VectorStoreIndex.from_vector_store(
                vector_store=vector_store,
                embed_model=self._embed_model,
            )
        except Exception:
            # Create empty index
            index = VectorStoreIndex(
                nodes=[],
                storage_context=storage_context,
                embed_model=self._embed_model,
            )

        self._indexes[session_id] = index
        return index

    async def index_document(
        self,
        session_id: str,
        parsed: ParsedDocument,
        metadata: FileMetadata,
    ) -> int:
        """Parse, chunk, embed, and index a document using LlamaIndex."""

        # Convert parsed pages into LlamaIndex Documents
        documents = []
        for page_num, page_text in parsed.pages.items():
            if not page_text.strip():
                continue
            doc = Document(
                text=page_text,
                metadata={
                    "file_id": parsed.file_id,
                    "filename": parsed.filename,
                    "page_number": page_num,
                },
            )
            documents.append(doc)

        if not documents:
            return 0

        # Chunk using SentenceSplitter
        nodes = self._splitter.get_nodes_from_documents(documents)

        # Add chunk_index metadata
        for i, node in enumerate(nodes):
            node.metadata["chunk_index"] = i

        # Get or create the index and insert nodes
        index = self._get_or_create_index(session_id)
        index.insert_nodes(nodes)

        # Create FTS index for BM25 hybrid search
        try:
            vector_store = self._vector_stores[session_id]
            if hasattr(vector_store, "_table") and vector_store._table is not None:
                vector_store._table.create_fts_index("text", replace=True)
                logger.info("fts_index_created", session_id=session_id)
        except Exception as e:
            logger.warning("fts_index_failed", error=str(e))

        logger.info(
            "document_indexed",
            session_id=session_id,
            file_id=parsed.file_id,
            pages=len(documents),
            chunks=len(nodes),
        )
        return len(nodes)

    async def search(
        self,
        query: str,
        session_id: str = "",
        top_k: int = 5,
    ) -> list[dict[str, Any]]:
        """Hybrid search (vector + BM25) via LlamaIndex query engine."""
        if not session_id:
            return []

        try:
            index = self._get_or_create_index(session_id)
        except Exception:
            return []

        # Use retriever for hybrid search
        retriever = index.as_retriever(
            similarity_top_k=top_k,
            vector_store_query_mode="hybrid",
        )

        try:
            retrieved_nodes = retriever.retrieve(query)
        except Exception as e:
            logger.warning("hybrid_search_failed_fallback_vector", error=str(e))
            # Fallback to vector-only search
            retriever = index.as_retriever(similarity_top_k=top_k)
            retrieved_nodes = retriever.retrieve(query)

        results = []
        for node_with_score in retrieved_nodes:
            node = node_with_score.node
            meta = node.metadata or {}
            results.append({
                "text": node.get_content(),
                "filename": meta.get("filename", ""),
                "page_number": meta.get("page_number", 0),
                "file_id": meta.get("file_id", ""),
                "score": round(node_with_score.score or 0.0, 4),
                "source": "hybrid",
            })

        logger.info(
            "document_search",
            query=query[:50],
            results=len(results),
            mode="hybrid",
        )
        return results

    async def remove_file(self, session_id: str, file_id: str) -> None:
        """Remove all chunks for a file from the index."""
        try:
            vector_store = self._vector_stores.get(session_id)
            if vector_store and hasattr(vector_store, "_table") and vector_store._table:
                vector_store._table.delete(f"metadata.file_id = '{file_id}'")
                # Rebuild FTS index
                vector_store._table.create_fts_index("text", replace=True)
        except Exception as e:
            logger.warning("remove_file_failed", error=str(e))
