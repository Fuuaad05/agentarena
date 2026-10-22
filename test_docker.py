from backend.sandbox.docker_runner import DockerSandbox


sandbox = DockerSandbox("playground_repo")

print("\nAGENTARENA DOCKER SANDBOX")
print("=" * 45)

result = sandbox.run_tests()

print("Success:", result["success"])
print("Summary:", result["summary"])

print("\nOutput:")
print(result.get("output", ""))