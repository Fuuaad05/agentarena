def can_fulfill_order(
    available_stock: int,
    requested_quantity: int,
) -> bool:
    """
    Return whether an order can be fulfilled.

    An order can be fulfilled when available stock
    is greater than or equal to the requested quantity.
    """

    if available_stock > requested_quantity:
        return True

    return False