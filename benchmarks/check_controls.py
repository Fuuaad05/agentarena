"""Curated fixture sanity check. No LLM/Tavily calls; never presented as model performance."""
import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.scenarios import SCENARIOS

def check_controls(docker=False):
    rows = []
    for scenario in SCENARIOS.values():
        row = {"scenario": scenario.id}
        for variant in ["buggy", "corrected"]:
            with tempfile.TemporaryDirectory() as tmp:
                repo = Path(tmp) / "repository"
                shutil.copytree(scenario.repo_path, repo, ignore=shutil.ignore_patterns("__pycache__", ".pytest_cache", "test_adversarial.py"))
                if variant == "corrected":
                    (repo / scenario.source_file).write_text(scenario.reference_file.read_text())
                # Only trusted, checked-in control tests run locally here.
                shutil.copyfile(ROOT / "benchmarks/control_tests" / f"{scenario.id}.py", repo / "test_control.py")
                if docker:
                    from backend.sandbox.docker_runner import DockerSandbox
                    original = DockerSandbox(str(repo)).run_tests(scenario.test_file)
                    boundary = DockerSandbox(str(repo)).run_tests("test_control.py")
                else:
                    def execute(filename):
                        run = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "--json-report", "--json-report-file=control-report.json", filename], cwd=repo, capture_output=True, text=True, timeout=20)
                        data = json.loads((repo / "control-report.json").read_text())
                        return {"success": run.returncode == 0, "exit_code": run.returncode, "summary": data.get("summary", {}), "output": run.stdout[-6000:]}
                    original = execute(scenario.test_file)
                    boundary = execute("test_control.py")
                row[variant] = {"original": original, "boundary": boundary}
        row["expected_result_observed"] = (row["buggy"]["original"]["success"] and row["corrected"]["original"]["success"] and row["buggy"]["boundary"]["exit_code"] == 1 and row["corrected"]["boundary"]["success"])
        rows.append(row)
    return {"kind": "curated_fixture_sanity_check", "runner": "Docker" if docker else "local pytest on trusted checked-in fixtures", "created_at": datetime.now(timezone.utc).isoformat(), "model_calls": 0, "tavily_calls": 0,
            "limitations": "These hand-written controls validate fixtures and corrected references; they do not measure an AI model or Tavily benefit.", "results": rows}

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--docker", action="store_true")
    args = parser.parse_args()
    report = check_controls(args.docker)
    for path in [ROOT / "benchmarks/results/curated-controls.json", ROOT / "frontend/public/evidence/curated-controls.json"]:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(report, indent=2))
    for row in report["results"]:
        print(row["scenario"], "PASS" if row["expected_result_observed"] else "FAIL")
    sys.exit(0 if all(row["expected_result_observed"] for row in report["results"]) else 1)
