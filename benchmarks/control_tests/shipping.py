from shipping import calculate_shipping

def test_exact_one_kg():
    assert calculate_shipping(1.0) == 5
