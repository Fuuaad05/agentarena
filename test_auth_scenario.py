from backend.pipeline import AgentArenaPipeline
from backend.scenarios import get_scenario


scenario = get_scenario("authentication")

pipeline = AgentArenaPipeline(
    repo_path=str(scenario.repo_path),
    scenario=scenario,
)

report = pipeline.run(
    scenario.default_bug_report
)

print("\nAUTHENTICATION SCENARIO RESULT")
print("=" * 45)

print("Status:", report["status"])
print("Evidence Score:", report["evidence_score"])
print("Patch Diff:")
print(report["patch_diff"])