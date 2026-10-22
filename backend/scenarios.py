from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Scenario:
    id: str
    name: str
    description: str
    repo_path: Path
    source_file: str
    test_file: str
    test_imports: str
    default_bug_report: str


SCENARIOS = {
    "discount": Scenario(
        id="discount",
        name="Discount Service",
        description="Investigate percentage discount calculation bugs.",
        repo_path=Path("playground_repo"),
        source_file="shop.py",
        test_file="test_shop.py",
        test_imports="from shop import calculate_discount",
        default_bug_report=(
            "Customers report that applying a 0% discount "
            "produces an incorrect total. Other discount "
            "percentages appear to work."
        ),
    ),
    "authentication": Scenario(
        id="authentication",
        name="Authentication Service",
        description="Investigate session expiration boundary bugs.",
        repo_path=Path("auth_repo"),
        source_file="auth.py",
        test_file="test_auth.py",
        test_imports="from auth import is_session_valid",
        default_bug_report=(
            "Users report that sessions remain valid at their "
            "exact expiration timestamp. Sessions should expire "
            "immediately when the expiration time is reached."
        ),
    ),
    "inventory": Scenario(
        id="inventory",
        name="Inventory Service",
        description="Investigate stock availability boundary bugs.",
        repo_path=Path("inventory_repo"),
        source_file="inventory.py",
        test_file="test_inventory.py",
        test_imports="from inventory import can_fulfill_order",
        default_bug_report=(
            "Customers cannot place orders when the requested "
            "quantity exactly matches available stock. "
            "Orders should be allowed when sufficient stock exists."
        ),
    ),
    "shipping": Scenario(
        id="shipping",
        name="Shipping Calculator",
        description=(
            "Investigate shipping price boundary conditions "
            "and incomplete test coverage."
        ),
        repo_path=Path("shipping_repo"),
        source_file="shipping.py",
        test_file="test_shipping.py",
        test_imports="from shipping import calculate_shipping",
        default_bug_report=(
            "Some customers report being charged the wrong "
            "shipping fee for packages near the 1 kg boundary. "
            "Shipping should cost $5 for weights up to and "
            "including 1 kg."
        ),
    ),
}


def get_scenario(scenario_id: str) -> Scenario:
    scenario = SCENARIOS.get(scenario_id)

    if scenario is None:
        raise ValueError(
            f"Unknown scenario: {scenario_id}"
        )

    return scenario


def list_scenarios():
    return [
        {
            "id": scenario.id,
            "name": scenario.name,
            "description": scenario.description,
            "default_bug_report": scenario.default_bug_report,
        }
        for scenario in SCENARIOS.values()
    ]