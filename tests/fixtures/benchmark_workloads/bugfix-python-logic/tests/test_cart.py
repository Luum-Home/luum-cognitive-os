from cart import total_cents


def test_total_includes_last_item():
    assert total_cents([100, 250, 50]) == 400


def test_empty_cart_is_zero():
    assert total_cents([]) == 0
