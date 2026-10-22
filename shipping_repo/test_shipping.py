import pytest

from shipping import calculate_shipping


def test_light_package():
    assert calculate_shipping(0.5) == 5


def test_medium_package():
    assert calculate_shipping(3) == 10


def test_heavy_package():
    assert calculate_shipping(8) == 20


def test_invalid_weight():
    with pytest.raises(ValueError):
        calculate_shipping(0)