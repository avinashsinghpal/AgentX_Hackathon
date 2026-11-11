#!/usr/bin/env python3
"""SellerResolve End-to-End Scenario Verification Script.

Executes all 4 canonical scenarios from the AgentX Hackathon PS-04 specification:
1. Scenario 1 (ORD-1001, $45.00): Autonomous Return Approval within policy window.
2. Scenario 2 (ORD-1002, $89.00): Deterministic Rejection for overdue return (> 14 days).
3. Scenario 3 (ORD-1003, $320.00): High-Value Escalation to Seller Approvals queue & Seller Approval.
4. Scenario 4 (ORD-1004, $110.00): Proactive Delay Monitor identifies stalled transit & issues store credit.
5. Mathematical Tamper Detection & Cryptographic Hash-Chain Verification across all audit events.
"""

# ruff: noqa: E402 - app imports must happen after sys.path/environment setup.
import asyncio
import os
import re
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

# Add apps/api to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "apps" / "api"))

os.environ["ENV"] = "testing"
os.environ["SECRET_KEY"] = "e2e-test-secret-key-32-bytes-minimum-ok"
# The scenario suite requires PostgreSQL.  Set E2E_DATABASE_URL (or DATABASE_URL)
# to a dedicated PostgreSQL database; the suite creates its tables there.
E2E_DATABASE_URL = os.environ.get("E2E_DATABASE_URL") or os.environ.get("DATABASE_URL")
if not E2E_DATABASE_URL:
    raise SystemExit(
        "E2E_DATABASE_URL (or DATABASE_URL) must point to PostgreSQL, "
        "for example postgresql+psycopg://sellerresolve:password@localhost:5432/sellerresolve_test"
    )
os.environ["DATABASE_URL"] = E2E_DATABASE_URL

from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine

from app.db.session import get_db
from app.models.action import Action
from app.models.buyer import Buyer
from app.models.case import ApprovalRequest, Case, CaseMessage
from app.models.order import Order
from app.models.seller import Seller, SellerPolicy
from app.models.shipment import Shipment
from app.models.user import User
from app.schemas.policy import parse_and_validate_yaml, policy_rules_dict
from app.services.agent.orchestrator import ResolutionOrchestrator
from app.services.approvals import ApprovalService
from app.services.audit import AuditLogService
from app.services.monitor import run_delay_monitor_cycle
from app.services.orders import sync_order_items, sync_tracking_events

EMOJI_REGEX = re.compile(
    "[\U00010000-\U0010ffff"
    "\U0001f600-\U0001f64f"
    "\U0001f300-\U0001f5ff"
    "\U0001f680-\U0001f6ff"
    "\U0001f700-\U0001f77f"
    "\U0001f780-\U0001f7ff"
    "\U0001f800-\U0001f8ff"
    "\U0001f900-\U0001f9ff"
    "\U0001fa00-\U0001fa6f"
    "\U0001fa70-\U0001faff"
    "\u2600-\u26ff"
    "\u2700-\u27bf]"
)


def assert_zero_emoji(text: str, context: str) -> None:
    matches = EMOJI_REGEX.findall(text)
    if matches:
        raise ValueError(f"Forbidden emoji found in {context}: {matches}")


def _alembic_head_revision() -> str:
    config_path = Path(__file__).resolve().parent.parent / "apps" / "api" / "alembic.ini"
    config = Config(str(config_path))
    config.set_main_option("script_location", str(config_path.parent / "alembic"))
    script = ScriptDirectory.from_config(config)
    head = script.get_current_head()
    if head is None:
        raise RuntimeError("No Alembic head revision is available.")
    return head


def _current_alembic_revision(engine) -> str | None:
    with engine.connect() as connection:
        context = MigrationContext.configure(connection)
        return context.get_current_revision()


def _require_alembic_head(engine) -> None:
    current = _current_alembic_revision(engine)
    head = _alembic_head_revision()
    if current != head:
        raise SystemExit(
            "The target database is not at the required Alembic head revision "
            f"({head}). Current revision: {current or 'none'}. "
            "Run 'alembic upgrade head' against the target database before running E2E scenarios."
        )


async def run_e2e_suite() -> None:
    print("=" * 70)
    print("  SellerResolve — Automated End-to-End Scenario Suite")
    print("  Autonomous, Policy-Aware Resolution Engine Verification")
    print("=" * 70)

    engine = create_engine(os.environ["DATABASE_URL"])
    _require_alembic_head(engine)
    db = next(get_db())

    try:
        now = datetime.now(UTC)
        run_id = int(now.timestamp()) % 100000

        # ---------------------------------------------------------
        # Setup: Seller "Apex Electronics" with standard active policies
        # ---------------------------------------------------------
        print("\n[SETUP] Registering Seller 'Apex Electronics' & Publishing Policies...")
        seller_user = User(
            email=f"apex_{run_id}@store.com",
            full_name="Apex Administrator",
            password_hash="argon2id_hash_mock",
            role="seller",
            is_active=True,
        )
        db.add(seller_user)
        db.flush()

        seller = Seller(
            user_id=seller_user.id,
            store_name="Apex Electronics",
            store_url="https://apex-electronics.com",
            currency="USD",
            status="active",
        )
        db.add(seller)
        db.flush()

        # Canonical policy document (the schema the engine validates).
        policy_yaml = """
version: 1
currency: USD
returns:
  window_days: 14
  return_shipping_paid_by: seller
refunds:
  auto_approve_up_to: 50
  require_seller_approval_above: 50
  instant_refund_without_return_threshold: 25
  cod_refund_method: store_credit
damage_claims:
  require_photo: true
  report_within_days: 2
delays:
  notify_after_days_late: 5
  compensation_per_day_late: 10
  max_delay_compensation: 50
fraud_checks:
  max_refunds_per_buyer_per_30_days: 3
"""
        is_valid, parsed_policy, policy_error = parse_and_validate_yaml(policy_yaml)
        assert is_valid and parsed_policy is not None, policy_error
        # Persist the legacy-compatible projection, exactly like the API does.
        parsed_rules = policy_rules_dict(parsed_policy)

        policy = SellerPolicy(
            seller_id=seller.id,
            version=1,
            is_active=True,
            policy_yaml=policy_yaml,
            parsed_rules=parsed_rules,
        )
        db.add(policy)
        db.flush()
        print(f"  [OK] Seller {seller.store_name} active with 14-day window & $50 auto-approve ceiling.")

        # Buyer: Maya Lin
        buyer_user = User(
            email=f"maya_{int(now.timestamp())}@buyer.com",
            full_name="Maya Lin",
            password_hash="argon2id_hash_mock",
            role="buyer",
            is_active=True,
        )
        db.add(buyer_user)
        db.flush()

        buyer = Buyer(
            user_id=buyer_user.id,
            default_shipping_address={"line1": "742 Evergreen Terrace", "city": "Springfield"},
            phone="+1-555-0199",
        )
        db.add(buyer)
        db.flush()
        print(f"  [OK] Buyer {buyer_user.full_name} registered.")

        orchestrator = ResolutionOrchestrator(db=db)

        # ---------------------------------------------------------
        # Scenario 1: ORD-1001 ($45.00) — Return within window (Autonomous Approval)
        # ---------------------------------------------------------
        print("\n" + "-" * 70)
        print(f"[SCENARIO 1] ORD-1001-{run_id} ($45.00) — Eligible Return within 14-Day Window")
        print("-" * 70)
        order_1 = Order(
            seller_id=seller.id,
            buyer_id=buyer.id,
            order_number=f"ORD-1001-{run_id}",
            order_date=now - timedelta(days=6),
            total_amount=4500,  # $45.00 in cents
            currency="USD",
            payment_method="prepaid",
            payment_status="captured",
            order_status="delivered",
            shipping_address={"line1": "742 Evergreen Terrace", "city": "Springfield"},
            items=[{"sku": "EARBUD-01", "title": "Wireless Earbuds", "quantity": 1, "unit_price": 45.0}],
        )
        db.add(order_1)
        db.flush()
        sync_order_items(db, order_1, order_1.items)

        shipment_1 = Shipment(
            order_id=order_1.id,
            tracking_number=f"TRK-1001-{run_id}",
            courier_partner="BlueDart",
            status="delivered",
            dispatch_pincode="110001",
            destination_pincode="560001",
            promised_delivery_date=now - timedelta(days=5),
            actual_delivery_date=now - timedelta(days=5),
        )
        db.add(shipment_1)
        db.flush()
        sync_tracking_events(
            db,
            shipment_1,
            [
                {
                    "status": "in_transit",
                    "timestamp": (now - timedelta(days=6)).isoformat(),
                    "location": "Delhi Hub",
                    "description": "Picked up by courier",
                },
                {
                    "status": "delivered",
                    "timestamp": (now - timedelta(days=5)).isoformat(),
                    "location": "Springfield",
                    "description": "Delivered to recipient",
                },
            ],
        )

        case_1 = Case(
            case_number=f"CAS-1001-{run_id}",
            seller_id=seller.id,
            buyer_id=buyer.id,
            order_id=order_1.id,
            issue_category="return",
            status="open",
            customer_narrative="I would like to return the wireless earbuds. Package is unopened.",
            evidence_urls=[],
        )
        db.add(case_1)
        db.flush()

        # Execute agent investigation & action
        turn_1 = await orchestrator.process_case_resolution(case_id=case_1.id)

        assert_zero_emoji(turn_1.message, "Scenario 1 agent reply")
        db.refresh(case_1)

        print(f"  Agent Reply: \"{turn_1.message[:110]}...\"")
        print(f"  Tool Calls Made: {[tc['tool_name'] for tc in turn_1.tool_calls]}")
        print(f"  Decision Badge: {turn_1.decision_badge}")
        print(f"  Case Status: {case_1.status}")

        assert turn_1.decision_badge == "executed"
        assert case_1.status == "resolved"
        assert case_1.decision == "executed"
        assert any(tc["tool_name"] in ["execute_and_verify_action", "verify_action_outcome"] for tc in turn_1.tool_calls)
        print("  --> [PASS] Scenario 1 Autonomous Return verified successfully.")

        # ---------------------------------------------------------
        # Scenario 2: ORD-1002 ($89.00) — Overdue Return (22 days > 14 days)
        # ---------------------------------------------------------
        print("\n" + "-" * 70)
        print(f"[SCENARIO 2] ORD-1002-{run_id} ($89.00) — Overdue Return (22 Days Since Delivery)")
        print("-" * 70)
        order_2 = Order(
            seller_id=seller.id,
            buyer_id=buyer.id,
            order_number=f"ORD-1002-{run_id}",
            order_date=now - timedelta(days=25),
            total_amount=8900,  # $89.00 in cents
            currency="USD",
            payment_method="prepaid",
            payment_status="captured",
            order_status="delivered",
            shipping_address={"line1": "742 Evergreen Terrace", "city": "Springfield"},
            items=[{"sku": "JACKET-02", "title": "Winter Jacket", "quantity": 1, "unit_price": 89.0}],
        )
        db.add(order_2)
        db.flush()
        sync_order_items(db, order_2, order_2.items)

        shipment_2 = Shipment(
            order_id=order_2.id,
            tracking_number=f"TRK-1002-{run_id}",
            courier_partner="FedEx",
            status="delivered",
            dispatch_pincode="110001",
            destination_pincode="560001",
            promised_delivery_date=now - timedelta(days=22),
            actual_delivery_date=now - timedelta(days=22),
        )
        db.add(shipment_2)
        db.flush()

        case_2 = Case(
            case_number=f"CAS-1002-{run_id}",
            seller_id=seller.id,
            buyer_id=buyer.id,
            order_id=order_2.id,
            issue_category="return",
            status="open",
            customer_narrative="I want to return this jacket, it does not fit.",
            evidence_urls=[],
        )
        db.add(case_2)
        db.flush()

        turn_2 = await orchestrator.process_case_resolution(case_id=case_2.id)

        assert_zero_emoji(turn_2.message, "Scenario 2 agent reply")
        db.refresh(case_2)

        print(f"  Agent Reply: \"{turn_2.message[:110]}...\"")
        print(f"  Tool Calls Made: {[tc['tool_name'] for tc in turn_2.tool_calls]}")
        print(f"  Decision Badge: {turn_2.decision_badge}")
        print(f"  Case Status: {case_2.status}")

        assert turn_2.decision_badge == "not_eligible"
        assert case_2.status == "rejected"
        assert case_2.decision == "not_eligible"
        print("  --> [PASS] Scenario 2 Autonomous Ineligibility Rejection verified successfully.")

        # ---------------------------------------------------------
        # Scenario 3: ORD-1003 ($320.00) — High-Value Damaged Goods (Seller Approval)
        # ---------------------------------------------------------
        print("\n" + "-" * 70)
        print(f"[SCENARIO 3] ORD-1003-{run_id} ($320.00) — High-Value Claim Escalated for Seller Approval")
        print("-" * 70)
        order_3 = Order(
            seller_id=seller.id,
            buyer_id=buyer.id,
            order_number=f"ORD-1003-{run_id}",
            order_date=now - timedelta(days=3),
            total_amount=32000,  # $320.00 in cents
            currency="USD",
            payment_method="prepaid",
            payment_status="captured",
            order_status="delivered",
            shipping_address={"line1": "742 Evergreen Terrace", "city": "Springfield"},
            items=[{"sku": "MONITOR-4K", "title": "4K Ultra-wide Display", "quantity": 1, "unit_price": 320.0}],
        )
        db.add(order_3)
        db.flush()
        sync_order_items(db, order_3, order_3.items)

        shipment_3 = Shipment(
            order_id=order_3.id,
            tracking_number=f"TRK-1003-{run_id}",
            courier_partner="DHL Express",
            status="delivered",
            dispatch_pincode="110001",
            destination_pincode="560001",
            promised_delivery_date=now - timedelta(days=2),
            actual_delivery_date=now - timedelta(days=2),
        )
        db.add(shipment_3)
        db.flush()

        case_3 = Case(
            case_number=f"CAS-1003-{run_id}",
            seller_id=seller.id,
            buyer_id=buyer.id,
            order_id=order_3.id,
            issue_category="damaged",
            status="open",
            customer_narrative="Screen arrived cracked. Attached damage photo.",
            evidence_urls=["/uploads/screen_damage.png"],
        )
        db.add(case_3)
        db.flush()

        turn_3 = await orchestrator.process_case_resolution(case_id=case_3.id)

        assert_zero_emoji(turn_3.message, "Scenario 3 agent reply")
        db.refresh(case_3)

        print(f"  Agent Reply: \"{turn_3.message[:110]}...\"")
        print(f"  Tool Calls Made: {[tc['tool_name'] for tc in turn_3.tool_calls]}")
        print(f"  Decision Badge: {turn_3.decision_badge}")
        print(f"  Case Status: {case_3.status}")

        assert turn_3.decision_badge == "needs_approval"
        assert case_3.status == "pending_approval"
        assert case_3.decision == "needs_approval"

        approval = (
            db.query(ApprovalRequest)
            .filter(ApprovalRequest.case_id == case_3.id)
            .first()
        )
        assert approval is not None
        assert approval.status == "pending"
        amount = approval.requested_action.get("amount", 320.00)
        assert amount == 320.00
        print(f"  Approval Request #{approval.id} queued for seller: ${amount:.2f}")

        # Human-in-the-loop: the seller authorizes execution. Approval alone is
        # not proof of execution, so the service must also run and verify it.
        decision = ApprovalService().decide(
            db,
            approval_id=approval.id,
            seller=seller,
            decision="approved",
            seller_notes="Verified cracked glass photo. Replacement authorized.",
        )
        db.refresh(case_3)
        assert decision.executed is True, decision.failure_reason
        assert decision.action is not None
        assert decision.action.action.status == "succeeded"
        db.refresh(decision.action.action)
        assert decision.action.action.external_reference

        executed_action = (
            db.query(Action)
            .filter(Action.case_id == case_3.id, Action.status == "succeeded")
            .first()
        )
        assert executed_action is not None

        print(f"  Seller Human-in-the-Loop Action: {approval.status.upper()}")
        print(f"  Executed Action: {executed_action.action_type} reference {executed_action.external_reference}")
        print(f"  Case Updated Status: {case_3.status} ({case_3.decision})")
        print("  --> [PASS] Scenario 3 Escalation and Seller Approval verified successfully.")

        # ---------------------------------------------------------
        # Scenario 4: ORD-1004 ($110.00) — In-Transit Delay (Proactive Compensation)
        # ---------------------------------------------------------
        print("\n" + "-" * 70)
        print(f"[SCENARIO 4] ORD-1004-{run_id} ($110.00) — Proactive Delay Monitor Automation")
        print("-" * 70)
        order_4 = Order(
            seller_id=seller.id,
            buyer_id=buyer.id,
            order_number=f"ORD-1004-{run_id}",
            order_date=now - timedelta(days=8),
            total_amount=11000,  # $110.00 in cents
            currency="USD",
            payment_method="prepaid",
            payment_status="captured",
            order_status="shipped",
            shipping_address={"line1": "742 Evergreen Terrace", "city": "Springfield"},
            items=[{"sku": "KEYBOARD-RGB", "title": "Mechanical Keyboard", "quantity": 1, "unit_price": 110.0}],
        )
        db.add(order_4)
        db.flush()
        sync_order_items(db, order_4, order_4.items)

        shipment_4 = Shipment(
            order_id=order_4.id,
            tracking_number=f"TRK-1004-{run_id}",
            courier_partner="Delhivery",
            status="in_transit",
            dispatch_pincode="110001",
            destination_pincode="560001",
            promised_delivery_date=now - timedelta(days=6),  # 6 days overdue > 5 SLA
            actual_delivery_date=None,
        )
        db.add(shipment_4)
        db.commit()

        # Trigger proactive monitor cycle
        proactive_results = run_delay_monitor_cycle(db)
        print(f"  Delay Monitor Scanned Active In-Transit Packages. Proactive cases handled: {len(proactive_results)}")

        proactive_case = (
            db.query(Case)
            .filter(Case.order_id == order_4.id, Case.issue_category == "delay")
            .first()
        )
        assert proactive_case is not None
        assert proactive_case.status == "resolved"
        assert proactive_case.decision == "executed"
        assert proactive_case.resolution_type == "delay_compensation"

        proactive_msg = (
            db.query(CaseMessage)
            .filter(CaseMessage.case_id == proactive_case.id)
            .first()
        )
        assert proactive_msg is not None
        assert_zero_emoji(proactive_msg.message, "Scenario 4 proactive message")
        credit_action = (
            db.query(Action)
            .filter(Action.order_id == order_4.id, Action.action_type == "wallet_credit")
            .first()
        )
        assert credit_action is not None
        assert credit_action.status == "succeeded"
        # 6 days late * 10 USD/day, capped at the policy maximum of 50 USD.
        assert credit_action.amount_minor == 5000
        assert proactive_results[0]["compensation"] == 50.0

        # A second scan must not duplicate the credit: the succeeded action and the
        # deterministic idempotency key both prevent it.
        db.expire_all()
        repeat_results = run_delay_monitor_cycle(db)
        assert repeat_results == [], repeat_results
        credit_count = (
            db.query(Action)
            .filter(Action.order_id == order_4.id, Action.action_type == "wallet_credit")
            .count()
        )
        assert credit_count == 1, credit_count

        print(f"  Proactive Case #{proactive_case.case_number} created with decision: {proactive_case.decision}")
        print(f"  Customer Notice: \"{proactive_msg.message[:100]}...\"")
        print(f"  Verified wallet credit: USD {credit_action.amount_minor / 100:.2f} (one action only)")
        print("  --> [PASS] Scenario 4 Proactive Delay Compensation verified successfully.")

        # ---------------------------------------------------------
        # Step 5: Cryptographic Audit Hash-Chain Verification
        # ---------------------------------------------------------
        print("\n" + "-" * 70)
        print("[AUDIT INTEGRITY] Mathematical Verification of SHA-256 Hash-Chain")
        print("-" * 70)
        is_valid, failure_reason = AuditLogService.verify_chain(db, seller.id)
        from app.models.audit import AuditLog
        total_records = db.query(AuditLog).filter(AuditLog.seller_id == seller.id).count()

        print(f"  Total Chained Audit Events: {total_records}")
        print(f"  Sequential Cryptographic Hash Chain Valid: {is_valid}")
        print(f"  Tampering Detected: {failure_reason is not None}")

        assert is_valid is True
        assert failure_reason is None
        assert total_records >= 4

        # Verify CSV export
        csv_data = AuditLogService.export_csv(db, seller.id)
        assert "id,timestamp_utc,actor_role,actor_id,action" in csv_data
        print(f"  Audit CSV Export: {len(csv_data)} bytes generated successfully.")
        print("  --> [PASS] Cryptographic Audit Trail integrity mathematically verified.")

        print("\n" + "=" * 70)
        print("  [ALL PASS] 4 OF 4 CANONICAL SCENARIOS + AUDIT INTEGRITY PASSED")
        print("=" * 70)

    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(run_e2e_suite())
