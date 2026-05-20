"""File Repository — upload, delete, path management."""

from __future__ import annotations

import shutil
import uuid
from pathlib import Path

from contracts.requests import FileMetadata
from core.patterns import singleton

from app.config import settings


@singleton
class FileRepository:
    """Handles file storage, retrieval, and cleanup."""

    def __init__(self):
        self._dir = settings.upload_dir
        self._files: dict[str, dict] = {}

    async def save(self, session_id: str, file) -> FileMetadata:
        file_id = uuid.uuid4().hex[:8]
        session_dir = self._dir / session_id
        session_dir.mkdir(parents=True, exist_ok=True)

        filename = file.filename or "upload.pdf"
        dest = session_dir / f"{file_id}_{filename}"

        content = await file.read()
        dest.write_bytes(content)

        metadata = FileMetadata(
            file_id=file_id,
            filename=filename,
            pages=0,
            size=len(content),
        )
        self._files[file_id] = {
            "metadata": metadata,
            "path": dest,
            "session_id": session_id,
        }
        return metadata

    def get_path(self, file_id: str) -> Path:
        entry = self._files.get(file_id)
        if entry is None:
            raise FileNotFoundError(f"File {file_id} not found")
        return entry["path"]

    async def delete(self, file_id: str) -> None:
        entry = self._files.pop(file_id, None)
        if entry is None:
            raise FileNotFoundError(f"File {file_id} not found")
        path: Path = entry["path"]
        if path.exists():
            path.unlink()

    def list_files(self, session_id: str | None = None) -> list[dict]:
        results = []
        for fid, entry in self._files.items():
            if session_id and entry["session_id"] != session_id:
                continue
            m = entry["metadata"]
            results.append({
                "file_id": m.file_id,
                "filename": m.filename,
                "pages": m.pages,
                "size_kb": m.size / 1024,
            })
        return results

    async def cleanup_session(self, session_id: str) -> None:
        session_dir = self._dir / session_id
        if session_dir.exists():
            shutil.rmtree(session_dir)
        self._files = {
            k: v for k, v in self._files.items() if v["session_id"] != session_id
        }
