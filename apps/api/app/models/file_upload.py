from typing import TYPE_CHECKING, Optional

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.case import Case


class FileUpload(Base):
    __tablename__ = "file_uploads"

    uploader_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    case_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("cases.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )
    original_filename: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    stored_filename: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
    )
    mime_type: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
    )
    file_size_bytes: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    storage_path: Mapped[str] = mapped_column(
        String(512),
        nullable=False,
    )

    case: Mapped[Optional["Case"]] = relationship("Case", back_populates="files")
