from dataclasses import dataclass
from enum import Enum


class FailureCategory(str, Enum):
    ASSERTION_FAILURE = "ASSERTION_FAILURE"
    INVALID_TEST = "INVALID_TEST"
    EXECUTION_ERROR = "EXECUTION_ERROR"
    UNKNOWN = "UNKNOWN"
    PRODUCTION_EXCEPTION = "PRODUCTION_EXCEPTION"


@dataclass
class ClassifiedFailure:
    test_name: str
    category: FailureCategory
    explanation: str
    evidence: str


class FailureClassifier:

    def __init__(self, production_files=()):
        self.production_files = {str(name).replace("\\", "/") for name in production_files}

    def classify(self, test: dict) -> ClassifiedFailure:

        name = test.get(
            "name",
            "unknown",
        )

        error = test.get(
            "error",
            "",
        )

        crash = test.get("crash") or {}
        crash_path = str(crash.get("path", "")).replace("\\", "/")
        # Accept only the known workspace source, not a matching basename in
        # another directory or exception text copied into a generated test.
        in_source = any(crash_path in (name, "/workspace/" + name)
                        for name in self.production_files)
        kind = str(crash.get("message", "")).split(":", 1)[0]
        supported = {"AttributeError", "TypeError", "ValueError", "ZeroDivisionError",
                     "IndexError", "KeyError", "NameError", "UnboundLocalError",
                     "RuntimeError", "OverflowError"}
        if test.get("call_outcome") == "failed" and in_source and kind in supported:
            return ClassifiedFailure(
                test_name=name, category=FailureCategory.PRODUCTION_EXCEPTION,
                explanation="The test call raised an exception inside the production source. A defect verdict also requires this same suite to pass the corrected reference.",
                evidence=error,
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