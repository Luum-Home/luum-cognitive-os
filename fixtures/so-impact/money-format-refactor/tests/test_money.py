from src.catalog import format_catalog_price
from src.checkout import format_checkout_price


def test_catalog_price() -> None:
    assert format_catalog_price(1234) == "$12.34"


def test_checkout_price() -> None:
    assert format_checkout_price(500) == "$5.00"
