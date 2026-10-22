def calculate_discount(price: float, discount_percent: float) -> float:
    """Return the price after applying a percentage discount."""

    if discount_percent == 0:
        return 0

    discount = price * (discount_percent / 100)
    return price - discount
