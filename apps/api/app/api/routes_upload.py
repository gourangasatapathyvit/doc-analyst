"""File upload and management endpoints."""

from __future__ import annotations

import structlog
from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.services.file_service import FileRepository
from app.services.parse_service import ParseService
from app.services.vector_service import VectorService
from contracts.requests import UploadResponse

logger = structlog.get_logger()

router = APIRouter()
file_repo = FileRepository()
parse_service = ParseService()
vector_service = VectorService()


@router.post("/api/upload", response_model=UploadResponse)
async def upload_file(file: UploadFile = File(...), session_id: str = Form(...)):
    """Upload a document, parse it, chunk it, embed it, index it."""

    metadata = await file_repo.save(session_id, file)
    logger.info("file_saved", filename=metadata.filename, file_id=metadata.file_id)

    parsed = await parse_service.parse(metadata.file_id, file_repo.get_path(metadata.file_id))
    logger.info("file_parsed", filename=metadata.filename, pages=parsed.page_count)

    chunks_count = await vector_service.index_document(session_id, parsed, metadata)
    logger.info("file_indexed", filename=metadata.filename, chunks=chunks_count)

    return UploadResponse(
        file_id=metadata.file_id,
        filename=metadata.filename,
        pages=parsed.page_count,
        status="ready",
    )


@router.delete("/api/files/{file_id}")
async def delete_file(file_id: str, session_id: str):
    """Remove a file and its vector index chunks."""
    try:
        await file_repo.delete(file_id)
        await vector_service.remove_file(session_id, file_id)
        parse_service.remove(file_id)
        logger.info("file_deleted", file_id=file_id)
        return {"status": "deleted"}
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="File not found")
