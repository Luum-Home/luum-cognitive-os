from customers import normalize_customer_slug
from orders import normalize_order_id


def test_order_normalization():
    assert normalize_order_id(" Order  123 ") == "order-123"


def test_customer_normalization():
    assert normalize_customer_slug(" Jane  Doe ") == "jane-doe"
