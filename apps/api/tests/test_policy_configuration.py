"""End-to-end coverage of the seller policy configuration workflow.

Covers structured JSON -> Pydantic -> canonical YAML, YAML validation, explicit
confirmation, immutable version publication, seller isolation and the guarantee
that the engine evaluates exactly the active version.
"""

from __future__ import annotations

import copy

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.audit import AuditLog
from app.models.seller import Seller, SellerPolicy
from app.models.user import User
from app.schemas.policy import (
    PolicySchema,
    RefundsPolicy,
    parse_and_validate_yaml,
    policy_to_yaml,
)
from app.services.policies import PolicyConfigurationService
from app.services.policy.evaluator import PolicyEvaluationService
from tests.factories import (
    make_buyer,
    make_case,
    make_order,
    make_seller,
    make_shipment,
)

POLICIES = "/api/v1/seller/policies"


def register_seller(client: TestClient, email: str) -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/register/seller",
        json={
            "email": email,
            "password": "Password123!",
            "full_name": email.split("@")[0].title(),
            "store_name": f"Store {email.split('@')[0]}",
        },
    )
    assert response.status_code in (200, 201), response.text
    return {"Authorization": f"Bearer {response.json()['token']}"}


def seller_for(db: Session, email: str) -> Seller:
    user = db.query(User).filter(User.email == email).one()
    return db.query(Seller).filter(Seller.user_id == user.id).one()


def base_config(client: TestClient, headers: dict[str, str]) -> dict:
    active = client.get(f"{POLICIES}/active", headers=headers)
    assert active.status_code == 200, active.text
    return copy.deepcopy(active.json()["config"])


def test_structured_config_converts_to_canonical_yaml(client: TestClient) -> None:
    headers = register_seller(client, "structured_policy@test.com")

    active = client.get(f"{POLICIES}/active", headers=headers).json()
    assert active["has_policy"] is False
    assert active["version"] == 0
    assert active["next_version"] == 1
    assert active["currency"] == "INR"
    assert active["valid"] is True

    config = copy.deepcopy(active["config"])
    config["returns"].update({"window_days": 10, "eligible_categories": ["apparel", "electronics"]})
    config["refunds"].update(
        {
            "auto_approve_up_to": 2000,
            "require_seller_approval_above": 2000,
            "instant_refund_without_return_threshold": 500,
            "cod_refund_method": "bank_transfer",
        }
    )
    config["delays"].update(
        {
            "notify_after_days_late": 3,
            "compensation_per_day_late": 50,
            "max_delay_compensation": 250,
        }
    )
    config["damage_claims"].update({"auto_replacement_under_amount": 1500, "report_within_days": 4})
    config["fraud_checks"].update({"max_refunds_per_buyer_per_30_days": 2})

    validated = client.post(f"{POLICIES}/validate-config", headers=headers, json={"config": config})
    assert validated.status_code == 200, validated.text
    body = validated.json()
    assert body["valid"] is True
    # Nothing is renamed or discarded between the form and the schema.
    assert body["config"] == config
    assert body["monetary_minor"]["currency"] == "INR"
    assert body["monetary_minor"]["minor_unit_exponent"] == 2
    # Rupees are converted to paise exactly once, on the server.
    assert body["monetary_minor"]["refund_auto_approve_ceiling_minor"] == 200_000
    assert body["monetary_minor"]["delay_compensation_per_day_minor"] == 5_000
    assert body["monetary_minor"]["delay_compensation_max_minor"] == 25_000

    preview = client.post(f"{POLICIES}/preview", headers=headers, json={"config": config})
    assert preview.status_code == 200, preview.text
    rendered = preview.json()

    is_valid, parsed, error = parse_and_validate_yaml(rendered["policy_yaml"])
    assert is_valid is True, error
    assert parsed is not None
    assert parsed == PolicySchema.model_validate(config)
    assert "auto_approve_up_to: 2000" in rendered["policy_yaml"]
    assert rendered["monetary_minor"] == body["monetary_minor"]


def test_yaml_validation_round_trips_and_rejects_unknown_fields(client: TestClient) -> None:
    headers = register_seller(client, "yaml_policy@test.com")

    canonical = policy_to_yaml(PolicySchema())
    validated = client.post(
        f"{POLICIES}/validate", headers=headers, json={"policy_yaml": canonical}
    )
    assert validated.status_code == 200
    assert validated.json()["valid"] is True
    assert validated.json()["config"]["refunds"]["auto_approve_up_to"] == 500
    assert validated.json()["monetary_minor"]["refund_auto_approve_ceiling_minor"] == 50_000

    negative_window = client.post(
        f"{POLICIES}/validate",
        headers=headers,
        json={"policy_yaml": "returns:\n  window_days: -5\n"},
    )
    assert negative_window.status_code == 200
    assert negative_window.json()["valid"] is False
    assert "returns.window_days" in negative_window.json()["error"]

    unknown_field = client.post(
        f"{POLICIES}/validate",
        headers=headers,
        json={"policy_yaml": "refunds:\n  mystery_threshold: 10\n"},
    )
    assert unknown_field.status_code == 200
    assert unknown_field.json()["valid"] is False
    assert "mystery_threshold" in unknown_field.json()["error"]

    # The legacy alias is accepted but normalizes into the canonical field, and
    # the approval ceiling follows it instead of silently defaulting to 500.
    legacy = client.post(
        f"{POLICIES}/validate",
        headers=headers,
        json={"policy_yaml": "refunds:\n  auto_approve_max_amount: 75\n"},
    )
    assert legacy.status_code == 200
    assert legacy.json()["valid"] is True
    refunds = legacy.json()["config"]["refunds"]
    assert refunds["auto_approve_up_to"] == 75
    assert refunds["require_seller_approval_above"] == 75
    assert legacy.json()["monetary_minor"]["refund_auto_approve_ceiling_minor"] == 7_500


def test_publishing_edited_yaml_uses_the_yaml_validation_path(client: TestClient) -> None:
    headers = register_seller(client, "yaml_publish@test.com")

    edited = PolicySchema(
        currency="INR",
        refunds=RefundsPolicy(auto_approve_up_to=750, require_seller_approval_above=750),
    )
    yaml_text = policy_to_yaml(edited)

    unconfirmed = client.post(
        f"{POLICIES}/publish",
        headers=headers,
        json={"policy_yaml": yaml_text, "expected_active_version": 0},
    )
    assert unconfirmed.status_code == 400

    published = client.post(
        f"{POLICIES}/publish",
        headers=headers,
        json={
            "policy_yaml": yaml_text,
            "confirm": True,
            "expected_active_version": 0,
        },
    )
    assert published.status_code == 201, published.text
    body = published.json()
    assert body["source"] == "yaml"
    assert body["version"] == 1
    assert body["config"]["refunds"]["auto_approve_up_to"] == 750
    assert body["monetary_minor"]["refund_auto_approve_ceiling_minor"] == 75_000

    # The deprecated raw-YAML route delegates to the same service and still
    # requires explicit confirmation.
    legacy = client.post(
        POLICIES,
        headers=headers,
        json={
            "policy_yaml": yaml_text,
            "confirm": True,
            "expected_active_version": 1,
        },
    )
    assert legacy.status_code == 201, legacy.text
    assert legacy.json()["version"] == 2


def test_invalid_configurations_are_rejected(client: TestClient) -> None:
    headers = register_seller(client, "invalid_policy@test.com")
    config = base_config(client, headers)

    contradictory = copy.deepcopy(config)
    contradictory["refunds"]["auto_approve_up_to"] = 1000
    contradictory["refunds"]["require_seller_approval_above"] = 500
    assert (
        client.post(
            f"{POLICIES}/validate-config",
            headers=headers,
            json={"config": contradictory},
        ).status_code
        == 422
    )

    out_of_range = copy.deepcopy(config)
    out_of_range["returns"]["window_days"] = 200
    assert (
        client.post(
            f"{POLICIES}/validate-config",
            headers=headers,
            json={"config": out_of_range},
        ).status_code
        == 422
    )

    unknown = copy.deepcopy(config)
    unknown["refunds"]["extra_threshold"] = 10
    assert (
        client.post(
            f"{POLICIES}/validate-config",
            headers=headers,
            json={"config": unknown},
        ).status_code
        == 422
    )

    wrong_currency = copy.deepcopy(config)
    wrong_currency["currency"] = "USD"
    preview = client.post(f"{POLICIES}/preview", headers=headers, json={"config": wrong_currency})
    assert preview.status_code == 400
    assert "does not match the store currency" in preview.json()["error"]["message"]

    invalid_yaml = client.post(
        f"{POLICIES}/publish",
        headers=headers,
        json={"policy_yaml": "returns:\n  window_days: -1\n", "confirm": True},
    )
    assert invalid_yaml.status_code == 400

    missing_source = client.post(f"{POLICIES}/publish", headers=headers, json={"confirm": True})
    assert missing_source.status_code == 422


def test_publication_requires_confirmation_and_creates_immutable_versions(
    client: TestClient, db: Session
) -> None:
    headers = register_seller(client, "publish_policy@test.com")
    seller = seller_for(db, "publish_policy@test.com")

    config = base_config(client, headers)
    config["refunds"]["auto_approve_up_to"] = 2000
    config["refunds"]["require_seller_approval_above"] = 2000

    unconfirmed = client.post(
        f"{POLICIES}/publish",
        headers=headers,
        json={"config": config, "expected_active_version": 0},
    )
    assert unconfirmed.status_code == 400
    assert "confirmation" in unconfirmed.json()["error"]["message"].lower()
    assert db.query(SellerPolicy).filter(SellerPolicy.seller_id == seller.id).count() == 0

    first = client.post(
        f"{POLICIES}/publish",
        headers=headers,
        json={"config": config, "confirm": True, "expected_active_version": 0},
    )
    assert first.status_code == 201, first.text
    first_body = first.json()
    assert first_body["version"] == 1
    assert first_body["previous_version"] == 0
    assert first_body["source"] == "structured"
    assert first_body["config"]["version"] == 1
    assert len(first_body["content_sha256"]) == 64
    assert first_body["monetary_minor"]["refund_auto_approve_ceiling_minor"] == 200_000

    active = client.get(f"{POLICIES}/active", headers=headers).json()
    assert active["has_policy"] is True
    assert active["version"] == 1
    assert active["next_version"] == 2
    assert active["activated_at"] is not None
    assert active["config"]["refunds"]["auto_approve_up_to"] == 2000

    second_config = copy.deepcopy(config)
    second_config["refunds"]["auto_approve_up_to"] = 3000
    second_config["refunds"]["require_seller_approval_above"] = 3000
    second = client.post(
        f"{POLICIES}/publish",
        headers=headers,
        json={
            "config": second_config,
            "confirm": True,
            "expected_active_version": 1,
        },
    )
    assert second.status_code == 201, second.text
    assert second.json()["version"] == 2
    assert second.json()["previous_version"] == 1

    history = client.get(f"{POLICIES}/history", headers=headers).json()
    assert [item["version"] for item in history] == [2, 1]
    assert [item["is_active"] for item in history] == [True, False]
    assert history[0]["source"] == "structured"
    assert history[1]["refund_ceiling"] == 2000
    assert history[1]["refund_ceiling_minor"] == 200_000

    old = client.get(f"{POLICIES}/versions/1", headers=headers).json()
    new = client.get(f"{POLICIES}/versions/2", headers=headers).json()
    assert old["config"]["refunds"]["auto_approve_up_to"] == 2000
    assert new["config"]["refunds"]["auto_approve_up_to"] == 3000
    assert old["config"]["version"] == 1
    assert new["config"]["version"] == 2

    stored = (
        db.query(SellerPolicy)
        .filter(SellerPolicy.seller_id == seller.id, SellerPolicy.version == 1)
        .one()
    )
    assert stored.currency == "INR"
    assert stored.published_by_user_id == seller.user_id
    assert isinstance(stored.parsed_rules["refunds"]["auto_approve_up_to"], int)

    audit_actions = [
        row.action for row in db.query(AuditLog).filter(AuditLog.seller_id == seller.id).all()
    ]
    assert audit_actions.count("policy.published") == 2

    # A published version cannot be edited in place; a new version is required.
    stored.policy_yaml = stored.policy_yaml + "\n# tampered\n"
    with pytest.raises(ValueError, match="immutable"):
        db.commit()
    db.rollback()


def test_publication_rejects_stale_active_version(client: TestClient) -> None:
    headers = register_seller(client, "stale_policy@test.com")
    config = base_config(client, headers)

    first = client.post(
        f"{POLICIES}/publish",
        headers=headers,
        json={"config": config, "confirm": True, "expected_active_version": 0},
    )
    assert first.status_code == 201

    stale = client.post(
        f"{POLICIES}/publish",
        headers=headers,
        json={"config": config, "confirm": True, "expected_active_version": 0},
    )
    assert stale.status_code == 409
    assert "changed while you were editing" in stale.json()["error"]["message"]
    assert len(client.get(f"{POLICIES}/history", headers=headers).json()) == 1

    # Omitting the optimistic guard is allowed (legacy clients), but explicit
    # versions remain the only way to publish.
    without_guard = client.post(
        f"{POLICIES}/publish",
        headers=headers,
        json={"config": config, "confirm": True},
    )
    assert without_guard.status_code == 201
    assert without_guard.json()["version"] == 2


def test_policy_versions_are_isolated_per_seller(client: TestClient) -> None:
    seller_a = register_seller(client, "policy_a@test.com")
    seller_b = register_seller(client, "policy_b@test.com")

    config = base_config(client, seller_a)
    for expected in (0, 1):
        response = client.post(
            f"{POLICIES}/publish",
            headers=seller_a,
            json={
                "config": config,
                "confirm": True,
                "expected_active_version": expected,
            },
        )
        assert response.status_code == 201, response.text

    active_b = client.get(f"{POLICIES}/active", headers=seller_b).json()
    assert active_b["has_policy"] is False
    assert client.get(f"{POLICIES}/history", headers=seller_b).json() == []
    assert client.get(f"{POLICIES}/versions/1", headers=seller_b).status_code == 404
    assert client.get(f"{POLICIES}/versions/2", headers=seller_b).status_code == 404

    first_b = client.post(
        f"{POLICIES}/publish",
        headers=seller_b,
        json={"config": config, "confirm": True, "expected_active_version": 0},
    )
    assert first_b.status_code == 201
    assert first_b.json()["version"] == 1

    history_a = client.get(f"{POLICIES}/history", headers=seller_a).json()
    history_b = client.get(f"{POLICIES}/history", headers=seller_b).json()
    assert [item["version"] for item in history_a] == [2, 1]
    assert [item["version"] for item in history_b] == [1]


def test_engine_evaluates_the_exact_active_version(db: Session) -> None:
    seller = make_seller(db)
    buyer = make_buyer(db)
    order = make_order(db, seller, buyer, total_minor=4500, days_ago=2)
    make_shipment(db, order, status="delivered", actual_delivery_days_ago=1)
    case = make_case(db, order, category="return")

    service = PolicyConfigurationService(db)
    first = service.publish(
        seller,
        config=PolicySchema(
            currency=seller.currency,
            refunds=RefundsPolicy(auto_approve_up_to=40, require_seller_approval_above=40),
        ),
        expected_active_version=0,
        actor_user_id=seller.user_id,
    )
    assert first.version == 1

    evaluation = PolicyEvaluationService()
    high_ceiling = evaluation.evaluate_case(db, case, persist=True)
    assert high_ceiling.result.decision.value == "needs_approval"
    assert high_ceiling.result.reason_code == "APPROVAL_CEILING_EXCEEDED"
    assert high_ceiling.record.policy_version == 1
    assert high_ceiling.record.seller_policy_id == first.row.id

    second = service.publish(
        seller,
        config=PolicySchema(
            currency=seller.currency,
            refunds=RefundsPolicy(auto_approve_up_to=50, require_seller_approval_above=50),
        ),
        expected_active_version=1,
        actor_user_id=seller.user_id,
    )
    assert second.version == 2

    low_ceiling = evaluation.evaluate_case(db, case, persist=True)
    assert low_ceiling.result.decision.value == "eligible"
    assert low_ceiling.record.policy_version == 2
    assert low_ceiling.record.seller_policy_id == second.row.id

    active = service.get_active(seller)
    assert active.version == 2
    assert active.next_version == 3
    assert active.policy is not None
    assert active.policy.refunds.auto_approve_up_to == 50
