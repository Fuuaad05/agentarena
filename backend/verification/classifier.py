from dataclasses import dataclass
from enum import Enum


class FailureCategory(str, Enum):
    ASSERTION_FAILURE = "ASSERTION_FAILURE"
    INVALID_TEST = "INVALID_TEST"
    EXECUTION_ERROR = "EXECUTION_ERROR"
    UNKNOWN = "UNKNOWN"


@dataclass
class ClassifiedFailure:
    test_name: str
    category: FailureCategory
    explanation: str
    evidence: str


class FailureClassifier:

    def classify(self, test: dict) -> ClassifiedFailure:

        name = test.get(
            "name",
            "unknown",
        )

        error = test.get(
            "error",
            "",
        )

        if "AssertionError" in error:

            return ClassifiedFailure(
                test_name=name,
                category=FailureCategory.ASSERTION_FAILURE,
                explanation=(
                    "The test assertion failed. "
                    "This may indicate a functional defect."
                ),
                evidence=error,
            )

        if any(
            keyword in error
            for keyword in [
                "NameError",
                "SyntaxError",
                "ImportError",
                "ModuleNotFoundError",
                "IndentationError",
            ]
        ):

            return ClassifiedFailure(
                test_name=name,
                category=FailureCategory.INVALID_TEST,
                explanation=(
                    "The generated test could not execute "
                    "correctly due to a code or import error."
                ),
                evidence=error,
            )

        if any(
            keyword in error
            for keyword in [
                "TimeoutError",
                "MemoryError",
                "OSError",
            ]
        ):

            return ClassifiedFailure(
                test_name=name,
                category=FailureCategory.EXECUTION_ERROR,
                explanation=(
                    "Test execution encountered "
                    "an environment or runtime error."
                ),
                evidence=error,
            )

        return ClassifiedFailure(
            test_name=name,
            category=FailureCategory.UNKNOWN,
            explanation=(
                "The failure could not be classified "
                "automatically."
            ),
            evidence=error,
        )