"""Case evidence association.

``file_uploads.case_id`` is the authoritative link between an uploaded file and
a case.  ``cases.evidence_urls`` remains as a compatibility projection for the
existing API/UI and for legacy references (paths or ids captured before file
records existed); it is maintained only here.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.case import Case
from app.models.file_upload import FileUpload
from app.models.user import User


def case_evidence_ids(db: Session, case: Case) -> list[str]:
    ordered: list[str] = []
    seen: set[str] = set()

    rows = (
        db.query(FileUpload)
        .filter(FileUpload.case_id == case.id)
        .order_by(FileUpload.created_at.asc())
        .all()
    )
    for row in rows:
        if row.id not in seen:
            seen.add(row.id)
            ordered.append(row.id)

    legacy = case.evidence_urls if isinstance(case.evidence_urls, list) else []
    for reference in legacy:
        if reference and reference not in seen:
            seen.add(reference)
            ordered.append(reference)

    return ordered


def attach_case_evidence(
    db: Session,
    case: Case,
    references: list[str],
    *,
    uploader_id: str | None = None,
) -> list[str]:
    """Attach uploaded files to a case and refresh the compatibility projection."""
    for reference in references or []:
        file = db.query(FileUpload).filter(FileUpload.id == reference).first()
        if file is None:
            continue
        if file.case_id is not None and file.case_id != case.id:
            # A file may only belong to one case; never steal another case's evidence.
            continue
        if uploader_id is not None and file.uploader_id != uploader_id:
            # Only the uploader may attach their own file.
            continue
        file.case_id = case.id

    db.flush()
    case.evidence_urls = case_evidence_ids(db, case)
    return case.evidence_urls


def can_access_case(db: Session, user: User, case: Case) -> bool:
    """Server-side ownership check for a case and everything attached to it."""
    if user.role == "buyer":
        buyer = getattr(user, "buyer", None)
        return buyer is not None and case.buyer_id == buyer.id

    if user.role == "seller":
        seller = getattr(user, "seller", None)
        return seller is not None and case.seller_id == seller.id

    return False


def can_access_file(db: Session, user: User, record: FileUpload) -> bool:
    """Server-side ownership check for evidence downloads."""
    if record.uploader_id == user.id:
        return True

    if not record.case_id:
        return False

    case = db.query(Case).filter(Case.id == record.case_id).first()
    if case is None:
        return False

    return can_access_case(db, user, case)
