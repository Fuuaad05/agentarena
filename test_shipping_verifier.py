from pathlib import Path

from backend.agents.verifier import AdversarialVerifier
from backend.sandbox.docker_runner import DockerSandbox
from backend.scenarios import get_scenario


scenario = get_scenario("shipping")

repo = Path(scenario.repo_path)

source_code = (
    repo / scenario.source_file
).read_text(encoding="utf-8")

existing_tests = (
    repo / scenario.test_file
).read_text(encoding="utf-8")

print("\nAGENTARENA ADVERSARIAL BENCHMARK")
print("=" * 50)

sandbox = DockerSandbox(str(repo))

original = sandbox.run_tests(
    test_file=scenario.test_file
)

print("\nOriginal test results:")
print(original["summary"])

verifier = AdversarialVerifier()

verification = verifier.generate_tests(
    bug_report=scenario.default_bug_report,
    source_code=source_code,
    existing_tests=existing_tests,
    test_imports=scenario.test_imports,
)

generated_tests = verification["tests"]

print("\nVerifier analysis:")
print(verification["analysis"])

print("\nGenerated tests:")

for test in generated_tests:
    print("-", test["name"])

test_content = (
    "import pytest\n"
    f"{scenario.test_imports}\n\n"
)

for test in generated_tests:
    test_content += test["code"] + "\n\n"

test_path = repo / "test_adversarial.py"

test_path.write_text(
    test_content,
    encoding="utf-8"
)

adversarial = sandbox.run_tests(
    test_file="test_adversarial.py"
)

print("\nAdversarial test results:")
print(adversarial["summary"])

print("\nDetailed output:")
print(adversarial["output"])

if original["success"] and not adversarial["success"]:
    print(
        "\n✅ BENCHMARK SUCCESS: "
        "Adversarial verification exposed a defect "
        "missed by the original tests."
    )
else:
    print(
        "\nBenchmark completed. Review the results "
        "to determine whether any real defect was found."
    )