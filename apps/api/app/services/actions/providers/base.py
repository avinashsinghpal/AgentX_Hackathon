from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

SUCCESS_STATUSES = ("succeeded", "duplicate")


@dataclass
class ProviderOutcome:
    """Normalized result of a provider call.

    ``timeout`` means the outcome is *unknown*, never that the operation failed.
    """

    status: str  # "succeeded" | "failed" | "timeout" | "duplicate"
    reference: str | None = None
    payload: dict[str, Any] = field(default_factory=dict)
    error_code: str | None = None
    retryable: bool = False

    @property
    def ok(self) -> bool:
        return self.status in SUCCESS_STATUSES


class ActionProvider(ABC):
    """Mock integration boundary.  No real credentials or network calls."""

    name: str = "base"

    @abstractmethod
    def execute(
        self,
        action_type: str,
        idempotency_key: str,
        *,
        amount_minor: int | None,
        currency: str | None,
        metadata: dict[str, Any] | None = None,
    ) -> ProviderOutcome: ...

    @abstractmethod
    def verify(
        self,
        reference: str | None,
        *,
        amount_minor: int | None = None,
        currency: str | None = None,
    ) -> ProviderOutcome: ...
