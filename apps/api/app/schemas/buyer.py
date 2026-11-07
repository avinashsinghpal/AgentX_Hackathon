from typing import Any

from pydantic import BaseModel, Field


class SellerPublicItem(BaseModel):
    id: str
    store_name: str
    description: str | None = None
    categories: list[str] = Field(default_factory=list)
    return_window_days: int = 7
    auto_approve_max_amount: float = 2000.0
    shipping_fee_bearer: str = "seller"
    orders_count: int = 0


class InviteInfoResponse(BaseModel):
    valid: bool
    invite_token: str
    seller_name: str
    seller_id: str
    customer_email: str | None = None
    expires_at: str | None = None
    message: str | None = None


class InviteAcceptResponse(BaseModel):
    success: bool
    message: str
    seller_name: str
    seller_id: str


class OrderItemDetail(BaseModel):
    item_id: str
    sku: str | None = None
    title: str
    quantity: int
    unit_price: float
    total_price: float
    category: str | None = None


class BuyerOrderSummary(BaseModel):
    id: str
    order_number: str
    seller_id: str
    seller_name: str
    order_date: str
    total_amount: float
    currency: str
    payment_method: str
    payment_status: str
    order_status: str
    items_count: int
    items: list[dict[str, Any]] = Field(default_factory=list)
    tracking_number: str | None = None
    carrier: str | None = None
    delivery_date: str | None = None
    eligible_for_complaint: bool = True


class OrderLinkRequest(BaseModel):
    order_number: str
    seller_id: str | None = None


class CaseCreateRequest(BaseModel):
    order_id: str
    issue_category: str
    customer_narrative: str = Field(min_length=5, max_length=5000)
    evidence_urls: list[str] = Field(default_factory=list)


class CaseSummaryItem(BaseModel):
    id: str
    case_number: str
    order_number: str
    seller_id: str
    seller_name: str
    issue_category: str
    status: str
    decision: str | None = None
    created_at: str
    resolved_at: str | None = None


class CaseMessageItem(BaseModel):
    id: str
    sender_role: str
    message: str
    tool_calls: list[dict[str, Any]] | None = None
    decision_badge: str | None = None
    created_at: str


class CaseDetailResponse(BaseModel):
    case: CaseSummaryItem
    order: BuyerOrderSummary
    customer_narrative: str
    evidence_urls: list[str] = Field(default_factory=list)
    messages: list[CaseMessageItem] = Field(default_factory=list)
    outcome_details: dict[str, Any] | None = None
