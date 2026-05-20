"""Parse Service — LiteParse wrapper + page-level cache."""

from __future__ import annotations

from pathlib import Path

import structlog
from liteparse import LiteParse

from contracts.schemas import ParsedDocument
from core.patterns import singleton

logger = structlog.get_logger()


@singleton
class ParseService:
    """Parses documents with LiteParse and caches page-level text."""

    def __init__(self):
        self._parser = LiteParse()
        self._cache: dict[str, ParsedDocument] = {}

    async def parse(self, file_id: str, file_path: Path) -> ParsedDocument:
        if file_id in self._cache:
            return self._cache[file_id]

        result = self._parser.parse(str(file_path))

        pages: dict[int, str] = {}
        for page in result.pages:
            pages[page.pageNum] = page.text if hasattr(page, "text") else str(page)

        doc = ParsedDocument(
            file_id=file_id,
            filename=file_path.name,
            pages=pages,
            page_count=len(result.pages),
        )
        self._cache[file_id] = doc

        logger.info("document_parsed", file_id=file_id, pages=doc.page_count)
        return doc

    def get_page(self, filename: str, page_number: int) -> str | None:
        for doc in self._cache.values():
            if doc.filename.endswith(filename) or filename in doc.filename:
                return doc.pages.get(page_number)
        return None

    def remove(self, file_id: str) -> None:
        self._cache.pop(file_id, None)
