import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.file_upload import FileUpload
from app.models.user import User

ALLOWED_MIME_TYPES = {
    "image/jpeg": [b"\xff\xd8\xff"],
    "image/png": [b"\x89PNG\r\n\x1a\n"],
    "image/webp": [b"RIFF"],  # WebP starts with RIFF, bytes 8-12 WEBP
}


def validate_image_magic_bytes(header: bytes, mime_type: str) -> bool:
    """Validate that the file header matches known signatures."""
    if mime_type == "image/jpeg":
        return header.startswith(b"\xff\xd8\xff")
    if mime_type == "image/png":
        return header.startswith(b"\x89PNG\r\n\x1a\n")
    if mime_type == "image/webp":
        return len(header) >= 12 and header.startswith(b"RIFF") and header[8:12] == b"WEBP"
    return False


class FileUploadService:
    @staticmethod
    async def save_upload(
        db: Session,
        upload_file: UploadFile,
        uploader: User,
        case_id: str | None = None,
    ) -> FileUpload:
        # Check MIME type
        content_type = (upload_file.content_type or "").lower().split(";")[0].strip()
        if content_type not in ALLOWED_MIME_TYPES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported file type '{content_type}'. Allowed types: JPEG, PNG, WebP.",
            )

        # Read content and check size
        content = await upload_file.read()
        file_size = len(content)

        if file_size == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Empty file upload.",
            )

        if file_size > settings.MAX_UPLOAD_BYTES:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File size ({file_size} bytes) exceeds limit of {settings.MAX_UPLOAD_BYTES} bytes.",
            )

        # Validate magic bytes
        if not validate_image_magic_bytes(content[:16], content_type):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File signature does not match claimed MIME type.",
            )

        # Ensure upload dir exists
        upload_dir = Path(settings.UPLOAD_DIR)
        upload_dir.mkdir(parents=True, exist_ok=True)

        # Generate unique storage filename
        original_ext = Path(upload_file.filename or "evidence.jpg").suffix.lower()
        if not original_ext or original_ext not in [".jpg", ".jpeg", ".png", ".webp"]:
            original_ext = ".jpg" if content_type == "image/jpeg" else ".png"

        stored_filename = f"{uuid.uuid4().hex}{original_ext}"
        storage_path = str(upload_dir / stored_filename)

        with open(storage_path, "wb") as f:
            f.write(content)

        # Create DB record
        record = FileUpload(
            uploader_id=uploader.id,
            case_id=case_id,
            original_filename=upload_file.filename or "evidence",
            stored_filename=stored_filename,
            mime_type=content_type,
            file_size_bytes=file_size,
            storage_path=storage_path,
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        return record
