from datetime import UTC, datetime, timedelta

from conftest import TestingSessionLocal
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.main import app
from app.models.action import Action
from app.models.buyer import Buyer
from app.models.case import Case, CaseMessage
from app.models.order import Order
from app.models.seller import Seller
from app.models.shipment import Shipment
from app.models.user import User
from app.services.agent.orchestrator import ResolutionOrchestrator
from app.services.llm.client import FakeLLMClient


def create_chat_case(db: Session) -> tuple[User, Case]:
    seller_user = User(
        email="chat-seller@example.com",
        full_name="Chat Seller",
        password_hash="test",
        role="seller",
        is_active=True,
    )
    buyer_user = User(
        email="chat-buyer@example.com",
        full_name="Chat Buyer",
        password_hash="test",
        role="buyer",
        is_active=True,
    )
    db.add_all([seller_user, buyer_user])
    db.flush()
    seller = Seller(user_id=seller_user.id, store_name="Chat Store", status="active")
    buyer = Buyer(user_id=buyer_user.id)
    db.add_all([seller, buyer])
    db.flush()

    now = datetime.now(UTC)
    order = Order(
        seller_id=seller.id,
        buyer_id=buyer.id,
        order_number="ORD-CHAT-100",
        order_date=now - timedelta(days=2),
        total_amount=2500,
        currency="USD",
        payment_method="card",
        payment_status="captured",
        order_status="shipped",
        shipping_address={"city": "Portland"},
        items=[{"sku": "ITEM-1", "quantity": 1, "total_price": 25}],
    )
    db.add(order)
    db.flush()
    db.add(
        Shipment(
            order_id=order.id,
            courier_partner="Test Carrier",
            tracking_number="TRACK-CHAT-100",
            dispatch_pincode="97201",
            destination_pincode="97202",
            promised_delivery_date=now + timedelta(days=2),
            status="in_transit",
        )
    )
    case = Case(
        case_number="CAS-CHAT-100",
        seller_id=seller.id,
        buyer_id=buyer.id,
        order_id=order.id,
        status="resolved",
        issue_category="delay",
        customer_narrative="I need an update about my shipment.",
        evidence_urls=[],
        decision="not_eligible",
    )
    db.add(case)
    db.flush()
    db.add_all(
        [
            CaseMessage(
                case_id=case.id,
                sender_role="buyer",
                message=case.customer_narrative,
            ),
            CaseMessage(
                case_id=case.id,
                sender_role="agent",
                message="I have received your shipment question.",
            ),
        ]
    )
    db.commit()
    return buyer_user, case


def test_buyer_chat_followups_persist_tools_and_deduplicate(
    client: TestClient,
    db: Session,
    auth_headers_for_user,
    monkeypatch,
) -> None:
    buyer_user, case = create_chat_case(db)
    monkeypatch.setattr(
        "app.services.agent.orchestrator.get_llm_client",
        lambda: FakeLLMClient(),
    )
    headers = auth_headers_for_user(buyer_user.id, "buyer")

    first = client.post(
        f"/api/v1/buyer/cases/{case.id}/chat",
        headers=headers,
        json={"message": "Where is my package?", "client_message_id": "chat-turn-1"},
    )
    assert first.status_code == 200
    first_response = first.json()
    assert first_response["sender_role"] == "agent"
    assert first_response["tool_calls"]
    assert any(call["tool_name"] == "lookup_order" for call in first_response["tool_calls"])
    assert any(
        call["tool_name"] == "lookup_shipment" for call in first_response["tool_calls"]
    )

    repeated = client.post(
        f"/api/v1/buyer/cases/{case.id}/chat",
        headers=headers,
        json={"message": "Where is my package?", "client_message_id": "chat-turn-1"},
    )
    assert repeated.status_code == 200
    assert repeated.json()["id"] == first_response["id"]

    second = client.post(
        f"/api/v1/buyer/cases/{case.id}/chat",
        headers=headers,
        json={"message": "When should it arrive?", "client_message_id": "chat-turn-2"},
    )
    assert second.status_code == 200
    assert second.json()["id"] != first_response["id"]

    detail = client.get(f"/api/v1/buyer/cases/{case.id}", headers=headers)
    assert detail.status_code == 200
    messages = detail.json()["messages"]
    assert [message["message"] for message in messages].count("Where is my package?") == 1
    assert [message["message"] for message in messages].count("When should it arrive?") == 1
    assert sum(message["sender_role"] == "agent" for message in messages) == 3
    db.refresh(case)
    assert case.status == "resolved"
    assert case.decision == "not_eligible"
    assert db.query(Action).filter(Action.case_id == case.id).count() == 0

    changed_payload = client.post(
        f"/api/v1/buyer/cases/{case.id}/chat",
        headers=headers,
        json={"message": "A different message", "client_message_id": "chat-turn-1"},
    )
    assert changed_payload.status_code == 409


def test_buyer_chat_retry_after_agent_failure(
    client: TestClient,
    auth_headers_for_user,
    monkeypatch,
) -> None:
    api_db = TestingSessionLocal()
    previous_override = app.dependency_overrides[get_db]

    def override_api_db():
        yield api_db

    app.dependency_overrides[get_db] = override_api_db
    buyer_user, case = create_chat_case(api_db)
    monkeypatch.setattr(
        "app.services.agent.orchestrator.get_llm_client",
        lambda: FakeLLMClient(),
    )
    original = ResolutionOrchestrator.respond_to_follow_up
    calls = 0

    async def fail_once(self, *args, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 1:
            raise RuntimeError("temporary provider failure")
        return await original(self, *args, **kwargs)

    monkeypatch.setattr(ResolutionOrchestrator, "respond_to_follow_up", fail_once)
    headers = auth_headers_for_user(buyer_user.id, "buyer")
    payload = {"message": "Can you check the tracking?", "client_message_id": "retry-turn"}
    url = f"/api/v1/buyer/cases/{case.id}/chat"

    try:
        failed = client.post(url, headers=headers, json=payload)
        assert failed.status_code == 503
        retried = client.post(url, headers=headers, json=payload)
        assert retried.status_code == 200

        buyer_turns = (
            api_db.query(CaseMessage)
            .filter(
                CaseMessage.case_id == case.id,
                CaseMessage.sender_role == "buyer",
                CaseMessage.client_message_id == "retry-turn",
            )
            .all()
        )
        agent_turns = (
            api_db.query(CaseMessage)
            .filter(
                CaseMessage.case_id == case.id,
                CaseMessage.sender_role == "agent",
                CaseMessage.client_message_id == "retry-turn",
            )
            .all()
        )
        assert len(buyer_turns) == 1
        assert len(agent_turns) == 1
        assert calls == 2
    finally:
        app.dependency_overrides[get_db] = previous_override
        api_db.query(CaseMessage).filter(CaseMessage.case_id == case.id).delete()
        api_db.query(Case).filter(Case.id == case.id).delete()
        api_db.query(Shipment).filter(Shipment.order_id == case.order_id).delete()
        api_db.query(Order).filter(Order.id == case.order_id).delete()
        api_db.query(Buyer).filter(Buyer.user_id == buyer_user.id).delete()
        seller_user_id = api_db.query(Seller.user_id).filter(Seller.id == case.seller_id).one()[0]
        api_db.query(Seller).filter(Seller.id == case.seller_id).delete(
            synchronize_session=False
        )
        api_db.query(User).filter(User.id.in_([buyer_user.id, seller_user_id])).delete(
            synchronize_session=False
        )
        api_db.commit()
        api_db.close()


def test_buyer_chat_initial_turn_and_case_ownership(
    client: TestClient,
    db: Session,
    auth_headers_for_user,
    monkeypatch,
) -> None:
    buyer_user, case = create_chat_case(db)
    case.status = "investigating"
    case.decision = None
    db.commit()
    other_user = User(
        email="other-chat-buyer@example.com",
        full_name="Other Buyer",
        password_hash="test",
        role="buyer",
        is_active=True,
    )
    db.add(other_user)
    db.flush()
    other_buyer = Buyer(user_id=other_user.id)
    db.add(other_buyer)
    db.commit()

    async def process_initial(self, case_id: str):
        current_case = self.db.query(Case).filter(Case.id == case_id).one()
        current_case.status = "rejected"
        current_case.decision = "not_eligible"
        response = CaseMessage(
            case_id=case_id,
            sender_role="agent",
            message="I reviewed your request; no action was taken.",
            decision_badge="not_eligible",
        )
        self.db.add(response)
        self.db.commit()
        self.db.refresh(response)
        return response

    monkeypatch.setattr(ResolutionOrchestrator, "process_case_resolution", process_initial)
    headers = auth_headers_for_user(buyer_user.id, "buyer")
    sent = client.post(
        f"/api/v1/buyer/cases/{case.id}/chat",
        headers=headers,
        json={"message": "Please review this request.", "client_message_id": "initial-turn"},
    )
    assert sent.status_code == 200

    other_headers = auth_headers_for_user(other_user.id, "buyer")
    forbidden = client.post(
        f"/api/v1/buyer/cases/{case.id}/chat",
        headers=other_headers,
        json={"message": "Can I see this conversation?", "client_message_id": "other-turn"},
    )
    assert forbidden.status_code == 404
    db.refresh(case)
    assert case.status == "rejected"
    assert case.decision == "not_eligible"
