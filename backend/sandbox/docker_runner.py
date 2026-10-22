import json
import subprocess
import tempfile

from pathlib import Path


class DockerSandbox:

    def __init__(self, repo_path: str):
        self.repo_path = Path(repo_path).resolve()

        if not self.repo_path.is_dir():
            raise ValueError(
                f"Repository does not exist: {self.repo_path}"
            )

    def run_tests(self, test_file=None):

        with tempfile.TemporaryDirectory() as temp_dir:

            report_dir = Path(temp_dir).resolve()

            command = [
                "docker",
                "run",
                "--rm",

                "--network", "none",
                "--memory", "512m",
                "--cpus", "1",
                "--pids-limit", "128",

                "--cap-drop", "ALL",

                "--security-opt",
                "no-new-privileges",

                "--mount",
                (
                    f"type=bind,"
                    f"source={self.repo_path},"
                    f"target=/workspace,"
                    f"readonly"
                ),

                "--mount",
                (
                    f"type=bind,"
                    f"source={report_dir},"
                    f"target=/reports"
                ),

                "--tmpfs",
                "/tmp:rw,size=64m",

                "-w",
                "/workspace",

                "agentarena-sandbox",

                "python",
                "-m",
                "pytest",
                "-q",

                "-p",
                "no:cacheprovider",

                "--json-report",

                "--json-report-file="
                "/reports/report.json",
            ]

            if test_file:
                command.append(test_file)

            try:
                result = subprocess.run(
                    command,
                    capture_output=True,
                    text=True,
                    timeout=60,
                )

            except subprocess.TimeoutExpired:
                return {
                    "success": False,
                    "exit_code": -1,
                    "summary": {},
                    "tests": [],
                    "output": "Sandbox execution timed out.",
                }

            report_file = report_dir / "report.json"

            if not report_file.exists():
                return {
                    "success": False,
                    "exit_code": result.returncode,
                    "summary": {},
                    "tests": [],
                    "output": result.stdout + result.stderr,
                }

            report = json.loads(
                report_file.read_text(
                    encoding="utf-8"
                )
            )

            summary = report.get(
                "summary",
                {}
            )

            tests = []

            for test in report.get("tests", []):

                node_id = test.get(
                    "nodeid",
                    "unknown",
                )

                outcome = test.get(
                    "outcome",
                    "unknown",
                )

                call = test.get("call", {})

                longrepr = call.get(
                    "longrepr",
                    "",
                )

                tests.append({
                    "name": node_id,
                    "outcome": outcome,
                    "error": longrepr,
                })

            return {
                "success": result.returncode == 0,
                "exit_code": result.returncode,
                "summary": {
                    "total": summary.get(
                        "total", 0
                    ),
                    "passed": summary.get(
                        "passed", 0
                    ),
                    "failed": summary.get(
                        "failed", 0
                    ),
                    "error": summary.get(
                        "error", 0
                    ),
                },
                "tests": tests,
                "output": result.stdout + result.stderr,
            }