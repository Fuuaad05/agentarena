from shop import calculate_discount

def test_zero_discount():
    assert calculate_discount(100, 0) == 100
