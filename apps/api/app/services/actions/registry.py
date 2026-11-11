from __future__ import annotations

from app.services.actions.providers.base import ActionProvider
from app.services.actions.providers.mock_courier import MockCourierProvider
from app.services.actions.providers.mock_payment import MockPaymentProvider

PAYMENT_ACTIONS = frozenset({"refund", "wallet_credit"})
COURIER_ACTIONS = frozenset({"return_label"})


class ProviderRegistry:
    """Maps deterministic action types to their (mocked) provider."""

    def __init__(
        self,
        payment_provider: MockPaymentProvider | None = None,
        courier_provider: MockCourierProvider | None = None,
    ) -> None:
        self.payment = payment_provider or MockPaymentProvider()
        self.courier = courier_provider or MockCourierProvider()

    def provider_for(self, action_type: str) -> ActionProvider:
        if action_type in PAYMENT_ACTIONS:
            return self.payment
        if action_type in COURIER_ACTIONS:
            return self.courier
        raise ValueError(f"No provider registered for action type '{action_type}'")

    def reset(self) -> None:
        self.payment.reset()
        self.courier.reset()


_default_registry: ProviderRegistry | None = None


def get_provider_registry() -> ProviderRegistry:
    global _default_registry
    if _default_registry is None:
        _default_registry = ProviderRegistry()
    return _default_registry


def set_provider_registry(registry: ProviderRegistry | None) -> None:
    """Test seam: replace the process-wide mock provider registry."""
    global _default_registry
    _default_registry = registry if registry is not None else ProviderRegistry()
