from backend.scoring.trust_engine import (
    TrustEngine,
    TestResults,
)


engine = TrustEngine()

original = TestResults(
    total=3,
    passed=3,
    failed=0,
)

adversarial = TestResults(
    total=4,
    passed=4,
    failed=0,
)

report = engine.calculate(
    original=original,
    adversarial=adversarial,
)

print("\nAGENTARENA TRUST REPORT")
print("=" * 40)

print(f"Trust Score: {report.score}/100")
print(f"Status: {report.status.value}")

print(
    f"Original Tests: "
    f"{report.original_tests.passed}/"
    f"{report.original_tests.total}"
)

print(
    f"Adversarial Tests: "
    f"{report.adversarial_tests.passed}/"
    f"{report.adversarial_tests.total}"
)

print(f"\nExplanation: {report.explanation}")