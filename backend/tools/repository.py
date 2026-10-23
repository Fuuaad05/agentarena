from pathlib import Path
import subprocess
import sys
import json
from backend.sandbox.docker_runner import DockerSandbox

class RepositoryTools:
    def __init__(self, repo_path: str, allowed_files=None):
        self.root = Path(repo_path).resolve()
        self.allowed_files = set(allowed_files) if allowed_files else None

        if not self.root.exists():
            raise ValueError(f"Repository does not exist: {self.root}")

    def _safe_path(self, relative_path: str) -> Path:
        path = (self.root / relative_path).resolve()

        try:
            path.relative_to(self.root)
        except ValueError:
            raise ValueError("Access outside repository is forbidden.")

        return path

    def run_tests_structured(self, test_file=None):
        """
        Run pytest and return structured test results.
        """

        report_file = self.root / ".agentarena_report.json"

        command = [
            sys.executable,
            "-m",
            "pytest",
            "-q",
            "--json-report",
            f"--json-report-file={report_file}",
        ]

        if test_file:
            command.append(test_file)

        try:
            result = subprocess.run(
                command,
                cwd=self.root,
                capture_output=True,
                text=True,
                timeout=30,
            )

        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error": "Tests timed out after 30 seconds.",
                "summary": {
                    "total": 0,
                    "passed": 0,
                    "failed": 0,
                    "error": 1,
                },
            }

        if not report_file.exists():
            return {
                "success": False,
                "error": "Pytest did not produce a JSON report.",
                "output": result.stdout + result.stderr,
            }

        with open(report_file, "r", encoding="utf-8") as file:
            report = json.load(file)

        summary = report.get("summary", {})

        return {
            "success": result.returncode == 0,
            "summary": {
                "total": summary.get("total", 0),
                "passed": summary.get("passed", 0),
                "failed": summary.get("failed", 0),
                "error": summary.get("error", 0),
            },
            "output": result.stdout + result.stderr,
        }

    def list_files(self) -> str:
        files = []

        excluded_directories = {
            "__pycache__",
            ".pytest_cache",
            ".git",
            ".venv",
        }

        excluded_files = {
            ".agentarena_report.json",
            ".agentarena_docker_report.json",
        }

        for path in self.root.rglob("*"):
            if not path.is_file():
                continue

            relative = path.relative_to(self.root)

            if any(
                part in excluded_directories
                for part in relative.parts
            ):
                continue

            if path.name in excluded_files:
                continue

            files.append(str(relative))

        return "\n".join(sorted(files))

    def read_file(self, path: str) -> str:
        safe_path = self._safe_path(path)

        if not safe_path.exists():
            return f"ERROR: File does not exist: {path}"

        if not safe_path.is_file():
            return f"ERROR: Not a file: {path}"

        return safe_path.read_text(
            encoding="utf-8",
            errors="replace",
        )

    def write_file(self, path: str, content: str) -> str:
        safe_path = self._safe_path(path)

        if (self.allowed_files is not None and str(safe_path.relative_to(self.root)) not in self.allowed_files) or safe_path.name == "conftest.py" or safe_path.name.startswith("test_"):
            return (
                "ERROR: Modifying test files is forbidden. "
                "Fix the production code instead."
            )

        if safe_path.suffix != ".py":
            return (
                "ERROR: Only Python source files can be modified."
            )

        safe_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        safe_path.write_text(
            content,
            encoding="utf-8",
        )

        return f"Successfully wrote {path}"

    def run_tests(self) -> str:
        sandbox = DockerSandbox(str(self.root))

        result = sandbox.run_tests()

        return (
            f"Exit code: {result.get('exit_code', -1)}\n\n"
            f"{result.get('output', '')}"
        )