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
    score: float
    status: VerificationStatus
    original_tests: TestResults
    adversarial_tests: TestResults
    explanation: str


class TrustEngine:
    """
    Calculates a heuristic test-pass score.

    The score summarizes observed test outcomes.
    It is not a calibrated probability of correctness.
    """

    def calculate(
        self,
        original: TestResults,
        adversarial: TestResults,
        mode: str = "repair",
    ) -> TrustReport:

        if mode not in ("repair", "audit"):
            raise ValueError(
                f"Unsupported verification mode: {mode}"
            )

        original_rate = (
            original.passed / original.total
            if original.total > 0
            else 0
        )

        adversarial_rate = (
            adversarial.passed / adversarial.total
            if adversarial.total > 0
            else 0
        )

        score = round(
            original_rate * 60
            + adversarial_rate * 40,
            2,
        )

        if (
            original.total == 0
            or adversarial.total == 0
        ):

            status = VerificationStatus.INCONCLUSIVE

            explanation = (
                "Insufficient test evidence to "
                "reach a verification verdict."
            )

        elif (
            original.failed > 0
            or original.errors > 0
        ):

            status = VerificationStatus.REJECTED

            if mode == "audit":
                explanation = (
                    "The existing test suite detected "
                    "one or more failures in the "
                    "audited implementation."
                )
            else:
                explanation = (
                    "The proposed patch failed one "
                    "or more original tests."
                )

        elif (
            adversarial.failed > 0
            or adversarial.errors > 0
        ):

            status = VerificationStatus.REJECTED

            if mode == "audit":
                explanation = (
                    "Adversarial tests exposed "
                    "potential defects in the "
                    "audited implementation."
                )
            else:
                explanation = (
                    "Adversarial tests exposed "
                    "potential defects in the "
                    "proposed patch."
                )

        else:

            status = VerificationStatus.PASSED_CHECKS

            if mode == "audit":
                explanation = (
                    "The audited implementation "
                    "passed all executed original "
                    "and adversarial tests. "
                    "This does not guarantee "
                    "correctness."
                )
            else:
                explanation = (
                    "The proposed patch passed "
                    "all executed original and "
                    "adversarial tests. "
                    "This does not guarantee "
                    "correctness."
                )

        return TrustReport(
            score=score,
            status=status,
            original_tests=original,
            adversarial_tests=adversarial,
            explanation=explanation,
        )