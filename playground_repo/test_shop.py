from shop import calculate_discount


def test_twenty_percent_discount():
    assert calculate_discount(100, 20) == 80


def test_fifty_percent_discount():
    assert calculate_discount(200, 50) == 100


def test_full_discount():
    assert calculate_discount(100, 100) == 0