from backend.sandbox.docker_runner import DockerSandbox

from backend.verification.classifier import (
    FailureClassifier,
)


sandbox = DockerSandbox("shipping_repo")

result = sandbox.run_tests(
    test_file="test_adversarial.py"
)

print("\nAGENTARENA FAILURE CLASSIFICATION")
print("=" * 50)

print("Test summary:")
print(result["summary"])

classifier = FailureClassifier()

for test in result.get("tests", []):

    if test["outcome"] == "passed":
        continue

    classified = classifier.classify(test)

    print("\nTest:", classified.test_name)
    print("Category:", classified.category.value)
    print("Explanation:", classified.explanation)

    print("\nEvidence:")
    print(classified.evidence[:1000])