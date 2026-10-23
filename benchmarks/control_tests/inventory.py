from inventory import can_fulfill_order

def test_exact_stock():
    assert can_fulfill_order(10, 10) is True
