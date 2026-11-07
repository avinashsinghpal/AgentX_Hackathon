from typing import Any

from fastapi import APIRouter, Query, Response

from app.api.deps import CurrentSeller, DbSession
from app.models.audit import AuditLog
from app.services.audit import AuditLogService

router = APIRouter(prefix="/seller/audit", tags=["Seller Audit Log"])


@router.get("")
def list_audit_logs(
    seller: CurrentSeller,
    db: DbSession,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    action: str | None = Query(default=None),
) -> dict[str, Any]:
    query = db.query(AuditLog).filter(AuditLog.seller_id == seller.id)
    if action:
        query = query.filter(AuditLog.action == action)

    total = query.count()
    records = query.order_by(AuditLog.timestamp.desc()).offset(offset).limit(limit).all()

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "records": [
            {
                "id": r.id,
                "timestamp": r.timestamp.isoformat(),
                "actor_role": r.actor_role,
                "actor_id": r.actor_id,
                "action": r.action,
                "case_id": r.case_id,
                "payload": r.payload,
                "current_hash": r.current_hash,
                "prev_hash": r.prev_hash,
            }
            for r in records
        ],
    }


@router.get("/verify")
def verify_audit_chain(
    seller: CurrentSeller,
    db: DbSession,
) -> dict[str, Any]:
    is_valid, error_msg = AuditLogService.verify_chain(db, seller_id=seller.id)
    total_records = db.query(AuditLog).filter(AuditLog.seller_id == seller.id).count()
    return {
        "valid": is_valid,
        "record_count": total_records,
        "error": error_msg,
    }


@router.get("/export")
def export_audit_csv(
    seller: CurrentSeller,
    db: DbSession,
) -> Response:
    csv_content = AuditLogService.export_csv(db, seller_id=seller.id)
    filename = f"sellerresolve_audit_{seller.id[:8]}.csv"
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
