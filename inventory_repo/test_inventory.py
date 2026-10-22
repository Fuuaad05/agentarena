from inventory import can_fulfill_order


def test_more_stock_than_requested():
    assert can_fulfill_order(20, 5) is True


def test_less_stock_than_requested():
    assert can_fulfill_order(3, 10) is False


def test_zero_stock_cannot_fulfill_positive_order():
    assert can_fulfill_order(0, 5) is False