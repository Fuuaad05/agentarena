from backend.tools.repository import RepositoryTools


tools = RepositoryTools("playground_repo")

result = tools.run_tests_structured()

print("\nAGENTARENA STRUCTURED TEST REPORT")
print("=" * 45)

print("Success:", result["success"])
print("Summary:", result["summary"])
print("\nOutput:")
print(result.get("output", ""))