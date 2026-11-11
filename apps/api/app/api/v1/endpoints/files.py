import os
from typing import Any

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse

from app.api.deps import CurrentUser, DbSession
from app.models.case import Case
from app.models.file_upload import FileUpload
from app.services.evidence import can_access_case, can_access_file
from app.services.upload import FileUploadService

router = APIRouter(prefix="/files", tags=["Evidence & Files"])
uploads_router = APIRouter(prefix="/uploads", tags=["Evidence & Files"])


async def upload_file(
    db: DbSession,
    current_user: CurrentUser,
    file: UploadFile = File(...),
    case_id: str | None = Form(None),
) -> dict[str, Any]:
    if case_id:
        case = db.query(Case).filter(Case.id == case_id).first()
        if case is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Case not found.",
            )
        if not can_access_case(db, current_user, case):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to attach evidence to this case.",
            )

    record = await FileUploadService.save_upload(
        db=db,
        upload_file=file,
        uploader=current_user,
        case_id=case_id,
    )
    file_url = f"/api/v1/files/{record.id}"
    return {
        "file_id": record.id,
        "id": record.id,
        "filename": record.original_filename,
        "mime_type": record.mime_type,
        "size_bytes": record.file_size_bytes,
        "url": file_url,
        "file_url": file_url,
    }


def get_file(
    file_id: str,
    db: DbSession,
    current_user: CurrentUser,
) -> FileResponse:
    record = db.query(FileUpload).filter(FileUpload.id == file_id).first()
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Requested file does not exist.",
        )

    # Scoped authorization before touching the filesystem: uploader, or the
    # buyer/seller that owns the case.
    if not can_access_file(db, current_user, record):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to access this file.",
        )

    if not os.path.exists(record.storage_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Requested file does not exist.",
        )

    return FileResponse(
        path=record.storage_path,
        media_type=record.mime_type,
        filename=record.original_filename,
    )


router.add_api_route("/upload", upload_file, methods=["POST"], status_code=status.HTTP_201_CREATED)
router.add_api_route("/{file_id}", get_file, methods=["GET"])
uploads_router.add_api_route("", upload_file, methods=["POST"], status_code=status.HTTP_201_CREATED)
uploads_router.add_api_route("/{file_id}", get_file, methods=["GET"])
