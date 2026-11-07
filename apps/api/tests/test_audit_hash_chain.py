from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.audit import AuditLog
from app.services.audit import GENESIS_HASH, AuditLogService


def test_audit_hash_chain_sequential_integrity(db: Session) -> None:
    seller_id = "test-seller-chain-123"

    log1 = AuditLogService.log_action(
        db=db,
        action="order.investigate",
        actor_role="agent",
        seller_id=seller_id,
        payload={"order_id": "ORD-1"},
    )
    assert log1.prev_hash == GENESIS_HASH
    assert len(log1.current_hash) == 64

    log2 = AuditLogService.log_action(
        db=db,
        action="policy.evaluate",
        actor_role="agent",
        seller_id=seller_id,
        payload={"eligible": True, "ceiling": 500},
    )
    assert log2.prev_hash == log1.current_hash
    assert len(log2.current_hash) == 64

    log3 = AuditLogService.log_action(
        db=db,
        action="action.execute_refund",
        actor_role="agent",
        seller_id=seller_id,
        payload={"amount": 450},
    )
    assert log3.prev_hash == log2.current_hash

    # Verify chain passes
    is_valid, error = AuditLogService.verify_chain(db, seller_id=seller_id)
    assert is_valid is True
    assert error is None


def test_audit_tamper_detection(db: Session) -> None:
    seller_id = "test-seller-tamper-456"

    # Create 3 chained records
    AuditLogService.log_action(db, "step.1", "system", seller_id=seller_id, payload={"count": 1})
    log2 = AuditLogService.log_action(
        db, "step.2", "system", seller_id=seller_id, payload={"count": 2}
    )
    AuditLogService.log_action(db, "step.3", "system", seller_id=seller_id, payload={"count": 3})

    # Chain initially valid
    valid, _ = AuditLogService.verify_chain(db, seller_id=seller_id)
    assert valid is True

    # Tamper with record 2 payload directly in DB
    db_rec = db.query(AuditLog).filter(AuditLog.id == log2.id).first()
    assert db_rec is not None
    db_rec.payload = {"count": 9999}  # Modified payload!
    db.commit()

    # Chain must now fail verification
    is_valid, error_msg = AuditLogService.verify_chain(db, seller_id=seller_id)
    assert is_valid is False
    assert "Tampered record at index 1" in str(error_msg)


def test_audit_csv_export(client: TestClient, db: Session) -> None:
    reg_res = client.post(
        "/api/v1/auth/register/seller",
        json={
            "email": "export_seller@test.com",
            "password": "Password123!",
            "full_name": "Export Seller",
            "store_name": "Export Store",
        },
    )
    token = reg_res.json()["token"]
    seller_id = reg_res.json()["tenant_info"]["seller_id"]

    AuditLogService.log_action(
        db,
        action="store.connected",
        actor_role="seller",
        seller_id=seller_id,
        payload={"demo": True},
    )
    AuditLogService.log_action(
        db, action="policy.saved", actor_role="seller", seller_id=seller_id, payload={"version": 1}
    )

    res = client.get(
        "/api/v1/seller/audit/export",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    assert res.headers["content-type"].startswith("text/csv")
    csv_text = res.text

    assert "timestamp_utc,actor_role,actor_id,action" in csv_text
    assert "store.connected" in csv_text
    assert "policy.saved" in csv_text
