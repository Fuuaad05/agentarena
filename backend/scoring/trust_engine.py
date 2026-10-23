from dataclasses import dataclass
from enum import Enum

class VerificationStatus(str, Enum):
    PASSED_CHECKS = "PASSED_CHECKS"
    REJECTED = "REJECTED"
    INCONCLUSIVE = "INCONCLUSIVE"

@dataclass
class TestResults:
    total: int
    passed: int
    failed: int
    errors: int = 0

@dataclass
class TrustReport:
    score: float | None
    status: VerificationStatus
    original_tests: TestResults
    adversarial_tests: TestResults
    explanation: str

class TrustEngine:
    """A descriptive score, never a probability that code is correct."""
    def calculate(self, original, adversarial, mode="repair", *, validation_problem=None):
        if mode not in ("repair", "audit"):
            raise ValueError(f"Unsupported verification mode: {mode}")
        problems = []
        for name, tests in [("Original", original), ("Adversarial", adversarial)]:
            if tests.total <= 0:
                problems.append(f"{name} tests did not produce usable evidence.")
            if tests.errors:
                problems.append(f"{name} tests encountered execution or test-generation errors.")
            if tests.total > tests.passed + tests.failed + tests.errors:
                problems.append(f"{name} tests include skipped or unaccounted outcomes.")
            if min(tests.total, tests.passed, tests.failed, tests.errors) < 0 or tests.passed + tests.failed > tests.total:
                problems.append(f"{name} test counts are inconsistent.")
        if validation_problem:
            problems.append(validation_problem)
        if problems:
            return TrustReport(None, VerificationStatus.INCONCLUSIVE, original, adversarial, " ".join(problems))
        score = round(60 * original.passed / original.total + 40 * adversarial.passed / adversarial.total, 2)
        status = VerificationStatus.REJECTED if original.failed or adversarial.failed else VerificationStatus.PASSED_CHECKS
        description = "The audited implementation" if mode == "audit" else "The proposed patch"
        explanation = (f"{description} failed executed checks. Inspect the failure evidence and reference control."
                       if status == VerificationStatus.REJECTED else
                       f"{description} passed all executed checks. This does not establish the absence of other defects.")
        return TrustReport(score, status, original, adversarial, explanation)
