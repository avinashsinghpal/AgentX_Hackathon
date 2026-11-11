"""Policy configuration service: validation, YAML rendering and publication.

All serialization, activation and persistence live here so the API layer stays a
thin translation between HTTP and this service.  Publication is the only write
path: a new row is appended with the next monotonically increasing version and
the previous active row is deactivated in the same transaction, so the engine
always sees exactly one active version per seller.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.seller import Seller, SellerPolicy
from app.schemas.policy import (
    PolicySchema,
    default_policy,
    normalize_parsed_rules,
    parse_and_validate_yaml,
    policy_to_yaml,
)
from app.services.audit import AuditLogService


class PolicyValidationError(ValueError):
    """The submitted policy is syntactically or semantically unusable."""


class PolicyConflictError(RuntimeError):
    """The active policy changed while the seller was editing."""


class PolicyNotFoundError(LookupError):
    """No policy version with that number exists for this seller."""


@dataclass(frozen=True)
class PolicyDocument:
    has_policy: bool
    policy_id: str | None
    version: int
    next_version: int
    policy: PolicySchema | None
    policy_yaml: str
    parsed_rules: dict[str, Any]
    currency: str
    activated_at: datetime | None = None
    created_at: datetime | None = None
    source: str | None = None
    content_sha256: str | None = None

    @property
    def valid(self) -> bool:
        return self.policy is not None

    def canonical_yaml(self) -> str:
        if self.policy is None:
            return self.policy_yaml
        return policy_to_yaml(self.policy)


@dataclass(frozen=True)
class PublishedPolicy:
    row: SellerPolicy
    policy: PolicySchema
    previous_version: int
    content_sha256: str

    @property
    def version(self) -> int:
        return self.row.version


class PolicyConfigurationService:
    def __init__(self, db: Session) -> None:
        self.db = db

    # ------------------------------------------------------------------ reads
    def _active_row(self, seller_id: str, *, lock: bool = False) -> SellerPolicy | None:
        query = self.db.query(SellerPolicy).filter(
            SellerPolicy.seller_id == seller_id,
            SellerPolicy.is_active.is_(True),
        )
        if lock:
            query = query.with_for_update()
        return query.order_by(SellerPolicy.version.desc()).first()

    def _latest_version(self, seller_id: str) -> int:
        latest = (
            self.db.query(func.max(SellerPolicy.version))
            .filter(SellerPolicy.seller_id == seller_id)
            .scalar()
        )
        return int(latest or 0)

    def _document_from_row(self, row: SellerPolicy, latest_version: int) -> PolicyDocument:
        policy = normalize_parsed_rules(row.parsed_rules)
        if policy is None:
            valid, parsed, _ = parse_and_validate_yaml(row.policy_yaml or "")
            policy = parsed if valid else None

        currency = (row.currency or (policy.currency if policy else None) or "INR").upper()
        return PolicyDocument(
            has_policy=True,
            policy_id=row.id,
            version=row.version,
            next_version=max(latest_version, row.version) + 1,
            policy=policy,
            policy_yaml=row.policy_yaml or "",
            parsed_rules=dict(row.parsed_rules or {}),
            currency=currency,
            activated_at=row.activated_at,
            created_at=row.created_at,
            source=row.source,
            content_sha256=row.content_sha256,
        )

    def get_active(self, seller: Seller) -> PolicyDocument:
        latest_version = self._latest_version(seller.id)
        row = self._active_row(seller.id)
        if row is not None:
            return self._document_from_row(row, latest_version)

        policy = default_policy((seller.currency or "INR").upper())
        return PolicyDocument(
            has_policy=False,
            policy_id=None,
            version=0,
            next_version=latest_version + 1,
            policy=policy,
            policy_yaml=policy_to_yaml(policy),
            parsed_rules=policy.model_dump(mode="json"),
            currency=policy.currency,
        )

    def list_history(self, seller: Seller) -> list[SellerPolicy]:
        return (
            self.db.query(SellerPolicy)
            .filter(SellerPolicy.seller_id == seller.id)
            .order_by(SellerPolicy.version.desc())
            .all()
        )

    def get_version(self, seller: Seller, version: int) -> PolicyDocument:
        row = (
            self.db.query(SellerPolicy)
            .filter(
                SellerPolicy.seller_id == seller.id,
                SellerPolicy.version == version,
            )
            .first()
        )
        if row is None:
            raise PolicyNotFoundError(f"Policy version {version} was not found.")
        return self._document_from_row(row, self._latest_version(seller.id))

    # ------------------------------------------------------------- validation
    def _assert_publication_rules(self, seller: Seller, policy: PolicySchema) -> None:
        seller_currency = (seller.currency or "INR").upper()
        if policy.currency != seller_currency:
            raise PolicyValidationError(
                f"Policy currency {policy.currency} does not match the store currency "
                f"{seller_currency}. Amounts cannot be compared across currencies."
            )

        if policy.refunds.require_seller_approval_above != policy.refunds.auto_approve_up_to:
            raise PolicyValidationError(
                "refunds.require_seller_approval_above and refunds.auto_approve_up_to "
                "express the same decision boundary and must be equal "
                f"({policy.refunds.auto_approve_up_to} != "
                f"{policy.refunds.require_seller_approval_above})."
            )

    @staticmethod
    def publication_warnings(policy: PolicySchema) -> list[str]:
        warnings: list[str] = []
        if (
            policy.delays.compensation_per_day_late > 0
            and policy.delays.max_delay_compensation == 0
        ):
            warnings.append(
                "Delay compensation is disabled because max_delay_compensation is 0."
            )
        if (
            policy.damage_claims.require_warehouse_inspection_above
            and policy.damage_claims.require_warehouse_inspection_above
            < policy.damage_claims.auto_replacement_under_amount
        ):
            warnings.append(
                "Warehouse inspection threshold is below the automatic replacement "
                "amount; replacements will always require inspection."
            )
        return warnings

    def validate_config(self, policy: PolicySchema) -> PolicySchema:
        """Structured input is already schema-validated; normalize money semantics."""
        return policy

    def validate_yaml(
        self, yaml_text: str
    ) -> tuple[PolicySchema | None, str | None]:
        is_valid, parsed, error = parse_and_validate_yaml(yaml_text)
        return (parsed if is_valid else None), error

    def preview(self, seller: Seller, policy: PolicySchema) -> tuple[str, list[str]]:
        self._assert_publication_rules(seller, policy)
        return policy_to_yaml(policy), self.publication_warnings(policy)

    # ------------------------------------------------------------ publication
    def publish(
        self,
        seller: Seller,
        *,
        config: PolicySchema | None = None,
        policy_yaml: str | None = None,
        expected_active_version: int | None = None,
        actor_user_id: str | None = None,
    ) -> PublishedPolicy:
        has_config = config is not None
        has_yaml = bool(policy_yaml and policy_yaml.strip())
        if has_config == has_yaml:
            raise PolicyValidationError(
                "Provide exactly one of a structured config or raw YAML."
            )

        if config is not None:
            policy = config
            resolved_source = "structured"
        else:
            parsed, error = self.validate_yaml(policy_yaml or "")
            if parsed is None:
                raise PolicyValidationError(error or "Invalid policy YAML.")
            policy = parsed
            resolved_source = "yaml"

        self._assert_publication_rules(seller, policy)

        # Serialize version allocation per seller.  On PostgreSQL the row lock
        # makes concurrent publications wait and then observe the winner's
        # committed state; SQLite serializes writers at the database level.
        locked_seller = (
            self.db.query(Seller)
            .filter(Seller.id == seller.id)
            .with_for_update()
            .one_or_none()
        )
        if locked_seller is None:
            raise PolicyNotFoundError("Seller profile no longer exists.")

        active_rows = (
            self.db.query(SellerPolicy)
            .filter(
                SellerPolicy.seller_id == seller.id,
                SellerPolicy.is_active.is_(True),
            )
            .order_by(SellerPolicy.version.desc())
            .with_for_update()
            .all()
        )
        previous_version = active_rows[0].version if active_rows else 0

        if (
            expected_active_version is not None
            and expected_active_version != previous_version
        ):
            raise PolicyConflictError(
                "The active policy changed while you were editing "
                f"(expected v{expected_active_version}, active v{previous_version}). "
                "Reload the current policy before publishing."
            )

        for row in active_rows:
            # Older databases may contain more than one active row; the engine
            # picks the highest version, so deactivate all of them atomically.
            row.is_active = False
        if active_rows:
            self.db.flush()

        next_version = self._latest_version(seller.id) + 1
        policy = policy.model_copy(update={"version": next_version})
        canonical_yaml = policy_to_yaml(policy)
        digest = hashlib.sha256(canonical_yaml.encode("utf-8")).hexdigest()
        now = datetime.now(UTC)

        new_policy = SellerPolicy(
            seller_id=seller.id,
            version=next_version,
            is_active=True,
            policy_yaml=canonical_yaml,
            parsed_rules=policy.model_dump(mode="json"),
            currency=policy.currency,
            content_sha256=digest,
            source=resolved_source,
            published_by_user_id=actor_user_id or seller.user_id,
            activated_at=now,
        )
        self.db.add(new_policy)

        if locked_seller.onboarding_step < 4:
            locked_seller.onboarding_step = 4

        self.db.flush()

        AuditLogService.log_action(
            db=self.db,
            action="policy.published",
            actor_role="seller",
            actor_id=actor_user_id or seller.user_id,
            seller_id=seller.id,
            payload={
                "policy_id": new_policy.id,
                "version": next_version,
                "previous_version": previous_version,
                "currency": policy.currency,
                "source": resolved_source,
                "content_sha256": digest,
                "monetary_minor": policy.monetary_minor(),
                "refund_ceiling": policy.refunds.auto_approve_up_to,
                "return_window_days": policy.returns.window_days,
            },
            commit=False,
        )

        self.db.commit()
        self.db.refresh(new_policy)

        return PublishedPolicy(
            row=new_policy,
            policy=policy,
            previous_version=previous_version,
            content_sha256=digest,
        )
