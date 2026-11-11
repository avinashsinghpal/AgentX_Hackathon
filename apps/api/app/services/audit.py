import csv
import hashlib
import io
import json
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.audit import GLOBAL_CHAIN_KEY, AuditChainState, AuditLog

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
    canonical_payload = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    content = (
        f"{prev_hash}|{timestamp_iso}|{seller_id or ''}|{case_id or ''}|"
        f"{actor_id or ''}|{actor_role}|{action}|{canonical_payload}"
    )
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def chain_key_for(seller_id: str | None) -> str:
    return seller_id or GLOBAL_CHAIN_KEY


class AuditLogService:
    @staticmethod
    def _get_or_create_chain_state(
        db: Session, chain_key: str, seller_id: str | None
    ) -> AuditChainState:
        state = (
            db.query(AuditChainState)
            .filter(AuditChainState.chain_key == chain_key)
            # Serializes concurrent appends on PostgreSQL; SQLite ignores it and
            # the unique (chain_key, sequence) constraint still prevents duplicates.
            .with_for_update()
            .first()
        )
        if state is not None:
            return state

        latest = (
            db.query(AuditLog)
            .filter(AuditLog.chain_key == chain_key)
            .order_by(AuditLog.sequence.desc())
            .first()
        )
        state = AuditChainState(
            chain_key=chain_key,
            last_hash=latest.current_hash if latest else GENESIS_HASH,
            last_sequence=latest.sequence if latest else 0,
        )
        try:
            # Savepoint so a concurrent creator does not poison the caller's work.
            with db.begin_nested():
                db.add(state)
                db.flush()
        except IntegrityError:
            state = (
                db.query(AuditChainState)
                .filter(AuditChainState.chain_key == chain_key)
                .with_for_update()
                .one()
            )
        return state

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
        commit: bool = True,
    ) -> AuditLog:
        """Append an entry to the seller's tamper-evident hash chain.

        ``commit=False`` lets a caller record the audit entry inside the same
        transaction as the state transition it records.
        """
        payload = payload or {}
        ts = timestamp or datetime.now(UTC)
        ts_iso = format_canonical_iso(ts)
        chain_key = chain_key_for(seller_id)

        state = AuditLogService._get_or_create_chain_state(db, chain_key, seller_id)
        prev_hash = state.last_hash
        sequence = state.last_sequence + 1

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
            chain_key=chain_key,
            sequence=sequence,
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

        state.last_hash = current_hash
        state.last_sequence = sequence

        if commit:
            db.commit()
            db.refresh(audit_entry)
        else:
            db.flush()
        return audit_entry

    @staticmethod
    def verify_chain(
        db: Session,
        seller_id: str | None = None,
        *,
        check_head: bool = True,
    ) -> tuple[bool, str | None]:
        """
        Verifies the cryptographic integrity of the audit log chain.
        Returns (True, None) if completely valid, or (False, failure_reason) if
        tampering is detected.
        """
        chain_key = chain_key_for(seller_id)
        records = (
            db.query(AuditLog)
            .filter(AuditLog.chain_key == chain_key)
            .order_by(AuditLog.sequence.asc())
            .all()
        )

        expected_prev_hash = GENESIS_HASH
        for idx, rec in enumerate(records):
            if rec.prev_hash != expected_prev_hash:
                return (
                    False,
                    f"Broken link at index {idx} (record {rec.id}): "
                    f"prev_hash {rec.prev_hash} != expected {expected_prev_hash}",
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
                    f"Tampered record at index {idx} (record {rec.id}): "
                    f"hash mismatch {rec.current_hash} != recomputed {recomputed_hash}",
                )

            expected_prev_hash = rec.current_hash

        if check_head and records:
            state = (
                db.query(AuditChainState)
                .filter(AuditChainState.chain_key == chain_key)
                .first()
            )
            if state is not None and (
                state.last_hash != expected_prev_hash
                or state.last_sequence != records[-1].sequence
            ):
                return (
                    False,
                    "Chain head mismatch: the recorded chain head does not match the "
                    "latest audit entry.",
                )

        return True, None

    @staticmethod
    def export_csv(db: Session, seller_id: str | None = None) -> str:
        """
        Exports audit log records to CSV format.
        """
        chain_key = chain_key_for(seller_id)
        records = (
            db.query(AuditLog)
            .filter(AuditLog.chain_key == chain_key)
            .order_by(AuditLog.sequence.desc())
            .all()
        )

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
                "sequence",
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
                    rec.sequence,
                ]
            )

        return output.getvalue()
