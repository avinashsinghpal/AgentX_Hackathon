from __future__ import annotations

from decimal import Decimal
from typing import Any

import pytest

from app.services.orders import item_price_minor_from_legacy


@pytest.mark.parametrize(
    ("item", "expected"),
    [
        ({"unit_price": 4500}, 4500),
        ({"unit_price": 45.0}, 4500),
        ({"unit_price": Decimal("45")}, 45),
        ({"unit_price": Decimal("45.50")}, 4550),
        ({"unit_price": "45.50"}, 4550),
        ({"unit_price": 0}, 0),
        ({"unit_price": None}, 0),
        ({"unit_price": -100}, -100),
        ({"unit_price": -45.0}, -4500),
        ({"unit_price": "not-a-number"}, 0),
        ({"total_price": 89.5}, 8950),
        ({"unit_price_minor": 1234, "unit_price": 99.0}, 1234),
        ({"total_price_minor": 5678, "total_price": 99.0}, 5678),
        ({}, 0),
    ],
)
def test_item_price_minor_from_legacy(item: dict[str, Any], expected: int) -> None:
    assert item_price_minor_from_legacy(item) == expected


def test_explicit_minor_field_is_not_reinterpreted() -> None:
    assert item_price_minor_from_legacy({"unit_price_minor": 45.0}) == 45
    assert item_price_minor_from_legacy({"unit_price_minor": Decimal("45.25")}) == 45


def test_malformed_item_returns_zero() -> None:
    assert item_price_minor_from_legacy(None) == 0  # type: ignore[arg-type]
    assert item_price_minor_from_legacy("bad") == 0  # type: ignore[arg-type]
