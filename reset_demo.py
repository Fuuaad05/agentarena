from pathlib import Path


BROKEN_CODE = '''def calculate_discount(price: float, discount_percent: float) -> float:
    """Return the price after applying a percentage discount."""

    if discount_percent == 0:
        return 0

    discount = price * (discount_percent / 100)
    return price - discount
'''


path = Path("playground_repo/shop.py")

path.write_text(
    BROKEN_CODE,
    encoding="utf-8",
)

print("✓ Demo repository reset to broken state.")