from __future__ import annotations

import logging
from pathlib import Path

import aiofiles
from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.resume import Resume
from app.utils.file_utils import allowed_file, safe_stored_name

logger = logging.getLogger(__name__)


class FileServiceError(Exception):
    pass


async def save_upload(*, db: Session, user_id: int, upload: UploadFile) -> Resume:
    if not upload.filename:
        raise FileServiceError("Missing filename")

    if not allowed_file(upload.filename):
        raise FileServiceError(
            f"Extension not allowed. Allowed: {', '.join(sorted(settings.allowed_extensions))}"
        )

    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    stored_name = safe_stored_name(upload.filename)
    dest = settings.upload_dir / stored_name

    size = 0
    max_bytes = settings.max_upload_mb * 1024 * 1024
    async with aiofiles.open(dest, "wb") as out:
        while chunk := await upload.read(1024 * 1024):
            size += len(chunk)
            if size > max_bytes:
                dest.unlink(missing_ok=True)
                raise FileServiceError(f"File exceeds {settings.max_upload_mb} MB limit")
            await out.write(chunk)

    resume = Resume(
        user_id=user_id,
        original_filename=upload.filename,
        stored_path=str(dest.resolve()),
        mime_type=upload.content_type,
        status="uploaded",
    )
    db.add(resume)
    db.commit()
    db.refresh(resume)
    logger.info(
        "Upload complete resume_id=%s user_id=%s filename=%s bytes=%s",
        resume.id,
        user_id,
        upload.filename,
        size,
    )
    return resume


def delete_resume_file(resume: Resume) -> None:
    path = Path(resume.stored_path)
    path.unlink(missing_ok=True)
