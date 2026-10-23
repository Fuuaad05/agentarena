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
    reference_file: Path | None = None


PROJECT_ROOT = Path(__file__).resolve().parents[1]

SCENARIOS = {
    "discount": Scenario(
        id="discount",
        name="Discount Service",
        description="Investigate percentage discount calculation bugs.",
        repo_path=PROJECT_ROOT / "playground_repo",
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
        repo_path=PROJECT_ROOT / "auth_repo",
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
        repo_path=PROJECT_ROOT / "inventory_repo",
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
        repo_path=PROJECT_ROOT / "shipping_repo",
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

SCENARIOS["redirect"] = Scenario(
    id="redirect", name="Safe Redirect Review",
    description="Documentation-informed security review of post-login redirects using Python 3.11 urllib.parse.",
    repo_path=PROJECT_ROOT / "redirect_repo", source_file="redirects.py",
    test_file="test_redirects.py", test_imports="from redirects import safe_redirect",
    default_bug_report=(
        "Review this post-login redirect helper. Every returned URL must have scheme https "
        "and authority exactly app.example. Accept root-relative local paths and preserve "
        "their query strings and fragments. Resolving dot segments according to Python 3.11 "
        "urllib.parse.urljoin is allowed; paths need not be preserved byte-for-byte. "
        "Reject absolute destinations, network-path references with an authority, non-string "
        "inputs, backslashes, ASCII whitespace/control characters and malformed URLs; "
        "return https://app.example/ for rejected inputs. Consult Python 3.11 urllib.parse "
        "documentation and prioritize tests of the destination-origin invariant."
    ),
)
SCENARIOS["callback"] = Scenario(
    id="callback", name="Callback Query Review",
    description="Documentation-led investigation of data loss in payment callback query decoding.",
    repo_path=PROJECT_ROOT / "callback_repo", source_file="callbacks.py",
    test_file="test_callbacks.py", test_imports="from callbacks import parse_callback_query",
    default_bug_report=(
        "Some payment callbacks cannot be reconciled downstream even though the provider "
        "reports a valid signature. Failures correlate with optional metadata. Review the "
        "query-decoding helper: it must retain every submitted form field in order for "
        "downstream processing. Investigate Python 3.11 urllib.parse behavior and missing "
        "regression coverage; do not change the downstream signature algorithm."
    ),
)
from dataclasses import replace
for _id, _scenario in list(SCENARIOS.items()):
    SCENARIOS[_id] = replace(_scenario, reference_file=PROJECT_ROOT / "benchmarks" / "references" / _id / _scenario.source_file)



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