from pathlib import Path

from backend.agents.verifier import AdversarialVerifier
from backend.tools.repository import RepositoryTools


BUG_REPORT = """
Customers report that applying a 0% discount produces an
incorrect total. Other discount percentages appear to work.
"""


repo_path = Path("playground_repo")

source_code = (repo_path / "shop.py").read_text(
    encoding="utf-8"
)

existing_tests = (repo_path / "test_shop.py").read_text(
    encoding="utf-8"
)

print("\n🛡️ AgentArena Adversarial Verification")
print("=" * 45)

verifier = AdversarialVerifier()

print("\nGenerating adversarial tests using Nemotron...")

result = verifier.generate_tests(
    bug_report=BUG_REPORT,
    source_code=source_code,
    existing_tests=existing_tests,
)

print("\nVerifier analysis:")
print(result["analysis"])

generated_tests = result["tests"]

print(f"\nGenerated {len(generated_tests)} tests:")

for test in generated_tests:
    print(f" - {test['name']}")

test_file = repo_path / "test_adversarial.py"

test_content = (
    "import pytest\n"
    "from shop import calculate_discount\n\n\n"
)

for test in generated_tests:
    test_content += test["code"] + "\n\n"

test_file.write_text(
    test_content,
    encoding="utf-8",
)

print("\nRunning adversarial tests...")

tools = RepositoryTools(str(repo_path))

test_result = tools.run_tests()

print(test_result)

if "Exit code: 0" in test_result:
    print("\n✅ PATCH SURVIVED ADVERSARIAL VERIFICATION")
else:
    print("\n⚠️ ADVERSARIAL VERIFIER FOUND A FAILURE")