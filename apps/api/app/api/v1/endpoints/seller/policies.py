"""Seller policy configuration API.

Thin HTTP layer over :class:`app.services.policies.PolicyConfigurationService`.
Serialization, YAML rendering, version allocation and activation all live in the
service so the workflow cannot be bypassed by a different endpoint.
"""

from typing import NoReturn

from fastapi import APIRouter, HTTPException, status

from app.api.deps import CurrentSeller, DbSession
from app.models.seller import SellerPolicy
from app.schemas.policy import (
    normalize_parsed_rules,
    policy_to_yaml,
    to_minor_units,
)
from app.schemas.policy_config import (
    PolicyConfigRequest,
    PolicyConfigValidationResponse,
    PolicyDocumentResponse,
    PolicyHistoryItem,
    PolicyLegacyPublishRequest,
    PolicyPreviewResponse,
    PolicyPublishRequest,
    PolicyPublishResponse,
    PolicyYamlRequest,
    PolicyYamlValidationResponse,
    monetary_minor_model,
)
from app.services.policies import (
    PolicyConfigurationService,
    PolicyConflictError,
    PolicyDocument,
    PolicyNotFoundError,
    PolicyValidationError,
    PublishedPolicy,
)

router = APIRouter(prefix="/policies", tags=["Seller Policies"])


def _document_response(document: PolicyDocument) -> PolicyDocumentResponse:
    policy = document.policy
    return PolicyDocumentResponse(
        has_policy=document.has_policy,
        valid=document.valid,
        id=document.policy_id,
        version=document.version,
        next_version=document.next_version,
        currency=document.currency,
        policy_yaml=document.policy_yaml,
        config=policy,
        parsed_rules=(
            policy.model_dump(mode="json") if policy else dict(document.parsed_rules)
        ),
        monetary_minor=monetary_minor_model(policy) if policy else None,
        activated_at=document.activated_at,
        created_at=document.created_at,
        source=document.source,
        content_sha256=document.content_sha256,
    )


def _publish_response(published: PublishedPolicy) -> PolicyPublishResponse:
    row = published.row
    policy = published.policy
    return PolicyPublishResponse(
        success=True,
        id=row.id,
        version=row.version,
        previous_version=published.previous_version,
        currency=policy.currency,
        policy_yaml=row.policy_yaml,
        config=policy,
        parsed_rules=policy.model_dump(mode="json"),
        monetary_minor=monetary_minor_model(policy),
        activated_at=row.activated_at,
        created_at=row.created_at,
        source=row.source or "structured",
        content_sha256=published.content_sha256,
    )


def _history_item(row: SellerPolicy) -> PolicyHistoryItem:
    policy = normalize_parsed_rules(row.parsed_rules)
    refund_ceiling: int | None = None
    returns_window: int | None = None
    if policy is not None:
        refund_ceiling = policy.refunds.auto_approve_up_to
        returns_window = policy.returns.window_days
    elif isinstance(row.parsed_rules, dict):
        refunds = row.parsed_rules.get("refunds") or {}
        returns = row.parsed_rules.get("returns") or {}
        if isinstance(refunds, dict):
            raw_ceiling = refunds.get(
                "auto_approve_up_to", refunds.get("auto_approve_max_amount")
            )
            if isinstance(raw_ceiling, int) and not isinstance(raw_ceiling, bool):
                refund_ceiling = raw_ceiling
        if isinstance(returns, dict):
            raw_window = returns.get("window_days")
            if isinstance(raw_window, int) and not isinstance(raw_window, bool):
                returns_window = raw_window

    refund_ceiling_minor: int | None = None
    if refund_ceiling is not None:
        try:
            refund_ceiling_minor = to_minor_units(refund_ceiling)
        except (TypeError, ValueError):
            refund_ceiling_minor = None
            refund_ceiling = None

    return PolicyHistoryItem(
        id=row.id,
        version=row.version,
        is_active=row.is_active,
        currency=(row.currency or "INR").upper(),
        created_at=row.created_at,
        activated_at=row.activated_at,
        source=row.source,
        content_sha256=row.content_sha256,
        returns_window=returns_window,
        refund_ceiling=refund_ceiling,
        refund_ceiling_minor=refund_ceiling_minor,
    )


def _raise_validation_error(exc: PolicyValidationError) -> NoReturn:
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=str(exc),
    ) from exc


@router.get("/active", response_model=PolicyDocumentResponse)
def get_active_policy(
    seller: CurrentSeller,
    db: DbSession,
) -> PolicyDocumentResponse:
    """Active version, or the baseline template when nothing is published."""
    document = PolicyConfigurationService(db).get_active(seller)
    return _document_response(document)


@router.get("/history", response_model=list[PolicyHistoryItem])
def get_policy_history(
    seller: CurrentSeller,
    db: DbSession,
) -> list[PolicyHistoryItem]:
    rows = PolicyConfigurationService(db).list_history(seller)
    return [_history_item(row) for row in rows]


@router.get("/versions/{version}", response_model=PolicyDocumentResponse)
def get_policy_version(
    version: int,
    seller: CurrentSeller,
    db: DbSession,
) -> PolicyDocumentResponse:
    """Read one immutable version, scoped to the authenticated seller."""
    try:
        document = PolicyConfigurationService(db).get_version(seller, version)
    except PolicyNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    return _document_response(document)


@router.post("/validate-config", response_model=PolicyConfigValidationResponse)
def validate_policy_config(
    data: PolicyConfigRequest,
    _seller: CurrentSeller,
    db: DbSession,
) -> PolicyConfigValidationResponse:
    """Validate structured JSON input against ``PolicySchema``.

    FastAPI returns a 422 with the offending field paths when the payload does
    not satisfy the schema; this endpoint returns the normalized document and the
    minor-unit snapshot when it does.
    """
    policy = PolicyConfigurationService(db).validate_config(data.config)
    return PolicyConfigValidationResponse(
        valid=True,
        currency=policy.currency,
        config=policy,
        monetary_minor=monetary_minor_model(policy),
    )


@router.post("/preview", response_model=PolicyPreviewResponse)
def preview_policy(
    data: PolicyConfigRequest,
    seller: CurrentSeller,
    db: DbSession,
) -> PolicyPreviewResponse:
    """Render canonical YAML for a structured configuration without publishing."""
    service = PolicyConfigurationService(db)
    try:
        yaml_text, warnings = service.preview(seller, data.config)
    except PolicyValidationError as exc:
        _raise_validation_error(exc)
    return PolicyPreviewResponse(
        valid=True,
        currency=data.config.currency,
        config=data.config,
        monetary_minor=monetary_minor_model(data.config),
        policy_yaml=yaml_text,
        warnings=warnings,
    )


@router.post("/validate", response_model=PolicyYamlValidationResponse)
def validate_policy(
    data: PolicyYamlRequest,
    _seller: CurrentSeller,
    db: DbSession,
) -> PolicyYamlValidationResponse:
    """Validate manually edited YAML and return its canonical form on success."""
    service = PolicyConfigurationService(db)
    parsed, error = service.validate_yaml(data.policy_yaml)
    if parsed is None:
        return PolicyYamlValidationResponse(valid=False, error=error)

    canonical = policy_to_yaml(parsed)
    return PolicyYamlValidationResponse(
        valid=True,
        error=None,
        config=parsed,
        policy_yaml=canonical,
        parsed=parsed.model_dump(mode="json"),
        monetary_minor=monetary_minor_model(parsed),
    )


@router.post(
    "/publish",
    status_code=status.HTTP_201_CREATED,
    response_model=PolicyPublishResponse,
)
def publish_policy(
    data: PolicyPublishRequest,
    seller: CurrentSeller,
    db: DbSession,
) -> PolicyPublishResponse:
    """Publish a new immutable version after explicit confirmation."""
    if not data.confirm:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Explicit confirmation is required before a policy can be published.",
        )

    service = PolicyConfigurationService(db)
    try:
        published = service.publish(
            seller,
            config=data.config,
            policy_yaml=data.policy_yaml if data.config is None else None,
            expected_active_version=data.expected_active_version,
            actor_user_id=seller.user_id,
        )
    except PolicyValidationError as exc:
        _raise_validation_error(exc)
    except PolicyConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    except PolicyNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    return _publish_response(published)


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=PolicyPublishResponse,
    deprecated=True,
    summary="Publish raw YAML (legacy alias of /publish)",
)
def save_policy(
    data: PolicyLegacyPublishRequest,
    seller: CurrentSeller,
    db: DbSession,
) -> PolicyPublishResponse:
    """Backward-compatible raw-YAML publication; still requires confirmation."""
    if not data.confirm:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Explicit confirmation is required before a policy can be published.",
        )

    service = PolicyConfigurationService(db)
    try:
        published = service.publish(
            seller,
            policy_yaml=data.policy_yaml,
            expected_active_version=data.expected_active_version,
            actor_user_id=seller.user_id,
        )
    except PolicyValidationError as exc:
        _raise_validation_error(exc)
    except PolicyConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    except PolicyNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    return _publish_response(published)

