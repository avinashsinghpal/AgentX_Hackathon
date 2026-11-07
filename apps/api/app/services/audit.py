import csv
import hashlib
import io
import json
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from app.models.audit import AuditLog

GENESIS_HASH = "0000000000000000000000000000000000000000000000000000000000000000"


def format_canonical_iso(dt: datetime) -> str:
    """Format datetime into a canonical UTC ISO-8601 string across DB engines."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    else:
        dt = dt.astimezone(UTC)
    return dt.strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def compute_audit_hash(
    prev_hash: str,
    timestamp_iso: str,
    seller_id: str | None,
    case_id: str | None,
    actor_id: str | None,
    actor_role: str,
    action: str,
    payload: dict[str, Any],
) -> str:
    canonical_payload = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    content = (
        f"{prev_hash}|{timestamp_iso}|{seller_id or ''}|{case_id or ''}|"
        f"{actor_id or ''}|{actor_role}|{action}|{canonical_payload}"
    )
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


class AuditLogService:
    @staticmethod
    def log_action(
        db: Session,
        action: str,
        actor_role: str,
        actor_id: str | None = None,
        seller_id: str | None = None,
        case_id: str | None = None,
        payload: dict[str, Any] | None = None,
        timestamp: datetime | None = None,
    ) -> AuditLog:
        """
        Appends an action to the tamper-evident hash-chained audit log.
        """
        payload = payload or {}
        ts = timestamp or datetime.now(UTC)
        ts_iso = format_canonical_iso(ts)

        # Find latest record for this seller (or globally if seller_id is None) to get prev_hash
        query = db.query(AuditLog)
        if seller_id:
            query = query.filter(AuditLog.seller_id == seller_id)
        latest_record = query.order_by(AuditLog.timestamp.desc(), AuditLog.id.desc()).first()

        prev_hash = latest_record.current_hash if latest_record else GENESIS_HASH

        current_hash = compute_audit_hash(
            prev_hash=prev_hash,
            timestamp_iso=ts_iso,
            seller_id=seller_id,
            case_id=case_id,
            actor_id=actor_id,
            actor_role=actor_role,
            action=action,
            payload=payload,
        )

        audit_entry = AuditLog(
            seller_id=seller_id,
            case_id=case_id,
            actor_id=actor_id,
            actor_role=actor_role,
            action=action,
            payload=payload,
            prev_hash=prev_hash,
            current_hash=current_hash,
            timestamp=ts,
        )
        db.add(audit_entry)
        db.commit()
        db.refresh(audit_entry)
        return audit_entry

    @staticmethod
    def verify_chain(db: Session, seller_id: str | None = None) -> tuple[bool, str | None]:
        """
        Verifies the cryptographic integrity of the audit log chain.
        Returns (True, None) if completely valid, or (False, failure_reason) if tampering is detected.
        """
        query = db.query(AuditLog)
        if seller_id:
            query = query.filter(AuditLog.seller_id == seller_id)
        records = query.order_by(AuditLog.timestamp.asc(), AuditLog.id.asc()).all()

        expected_prev_hash = GENESIS_HASH
        for idx, rec in enumerate(records):
            if rec.prev_hash != expected_prev_hash:
                return (
                    False,
                    f"Broken link at index {idx} (record {rec.id}): prev_hash {rec.prev_hash} != expected {expected_prev_hash}",
                )

            recomputed_hash = compute_audit_hash(
                prev_hash=rec.prev_hash,
                timestamp_iso=format_canonical_iso(rec.timestamp),
                seller_id=rec.seller_id,
                case_id=rec.case_id,
                actor_id=rec.actor_id,
                actor_role=rec.actor_role,
                action=rec.action,
                payload=rec.payload,
            )

            if rec.current_hash != recomputed_hash:
                return (
                    False,
                    f"Tampered record at index {idx} (record {rec.id}): hash mismatch {rec.current_hash} != recomputed {recomputed_hash}",
                )

            expected_prev_hash = rec.current_hash

        return True, None

    @staticmethod
    def export_csv(db: Session, seller_id: str | None = None) -> str:
        """
        Exports audit log records to CSV format.
        """
        query = db.query(AuditLog)
        if seller_id:
            query = query.filter(AuditLog.seller_id == seller_id)
        records = query.order_by(AuditLog.timestamp.desc()).all()

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(
            [
                "id",
                "timestamp_utc",
                "actor_role",
                "actor_id",
                "action",
                "case_id",
                "seller_id",
                "payload_json",
                "current_hash",
                "prev_hash",
            ]
        )

        for rec in records:
            writer.writerow(
                [
                    rec.id,
                    format_canonical_iso(rec.timestamp),
                    rec.actor_role,
                    rec.actor_id or "",
                    rec.action,
                    rec.case_id or "",
                    rec.seller_id or "",
                    json.dumps(rec.payload, separators=(",", ":")),
                    rec.current_hash,
                    rec.prev_hash,
                ]
            )

        return output.getvalue()
