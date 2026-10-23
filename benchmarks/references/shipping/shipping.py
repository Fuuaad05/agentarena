def calculate_shipping(weight: float) -> float:
    """
    Calculate shipping cost.

    Business rules:
    - Weight must be positive.
    - Up to 1 kg: $5
    - Above 1 kg up to 5 kg: $10
    - Above 5 kg: $20
    """

    if weight <= 0:
        raise ValueError("Weight must be positive")

    if weight <= 1:
        return 5

    if weight <= 5:
        return 10

    return 20