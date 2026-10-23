"""Bounded Docker execution. The Docker socket is never mounted into a test container."""
import json
import os
import subprocess
import tempfile
import uuid
from pathlib import Path

class DockerSandbox:
    def __init__(self, repo_path):
        self.repo_path = Path(repo_path).resolve()
        if not self.repo_path.is_dir():
            raise ValueError(f"Repository does not exist: {self.repo_path}")

    def run_tests(self, test_file=None):
        name = "agentarena-" + uuid.uuid4().hex
        with tempfile.TemporaryDirectory() as tmp:
            reports = Path(tmp)
            # Only this throwaway directory is writable by the unprivileged test user.
            reports.chmod(0o777)
            command = ["docker", "run", "--rm", "--name", name, "--init", "--network", "none",
                       "--memory", "512m", "--cpus", "1", "--pids-limit", "128", "--cap-drop", "ALL",
                       "--security-opt", "no-new-privileges", "--read-only", "--user", "65532:65532",
                       "-e", "PYTHONDONTWRITEBYTECODE=1", "--mount", f"type=bind,source={self.repo_path},target=/workspace,readonly",
                       "--mount", f"type=bind,source={reports},target=/reports", "--tmpfs", "/tmp:rw,size=64m,mode=1777",
                       "-w", "/workspace", os.getenv("SANDBOX_IMAGE", "agentarena-sandbox"),
                       "python", "-m", "pytest", "-q", "-p", "no:cacheprovider", "--json-report", "--json-report-file=/reports/report.json"]
            if test_file:
                command.append(test_file)
            def unusable(message, exit_code=-1):
                return {"success": False, "exit_code": exit_code, "execution_error": message,
                        "summary": {"total": 0, "passed": 0, "failed": 0, "error": 1}, "tests": [], "output": message}
            try:
                result = subprocess.run(command, capture_output=True, text=True, timeout=int(os.getenv("SANDBOX_TIMEOUT_SECONDS", "60")))
                path = reports / "report.json"
                if not path.is_file() or path.stat().st_size > 2_000_000:
                    return unusable((result.stdout + result.stderr)[-12000:] or "No usable test report.", result.returncode)
                try:
                    report = json.loads(path.read_text())
                    raw = report["summary"]
                    summary = {k: int(raw.get(k, 0)) for k in ["total", "passed", "failed", "error", "skipped"]}
                    if min(summary.values()) < 0:
                        return unusable("Invalid negative report counts.")
                except (ValueError, KeyError, TypeError, OSError):
                    return unusable("Test runner returned an invalid JSON report.")
                tests = []
                for test in report.get("tests", []):
                    evidence = "\n".join(str(test.get(phase, {}).get("longrepr", "")) for phase in ["setup", "call", "teardown"]).strip()
                    call = test.get("call", {})
                    tests.append({"name": test.get("nodeid", "unknown"), "outcome": test.get("outcome", "unknown"), "error": evidence[:12000],
                                  "call_outcome": call.get("outcome"), "crash": call.get("crash", {})})
                errors = [c for c in report.get("collectors", []) if c.get("outcome") == "failed"]
                if errors:
                    summary["error"] = max(1, summary["error"])
                    tests.extend({"name": c.get("nodeid", "collection"), "outcome": "error", "error": str(c.get("longrepr", ""))[:12000]} for c in errors)
                if result.returncode not in (0, 1) or (result.returncode and not summary["failed"]):
                    summary["error"] = max(1, summary["error"])
                return {"success": result.returncode == 0, "exit_code": result.returncode,
                        "summary": summary, "tests": tests, "output": (result.stdout + result.stderr)[-16000:]}
            except subprocess.TimeoutExpired as error:
                def readable(value):
                    return value.decode("utf-8", errors="replace") if isinstance(value, bytes) else (value or "")
                partial = (readable(error.stdout) + readable(error.stderr))[-6000:]
                limit = os.getenv("SANDBOX_TIMEOUT_SECONDS", "60")
                return unusable(f"Sandbox exceeded the {limit}-second limit; container cleanup requested. " + partial)
            except OSError as error:
                return unusable(f"Docker unavailable: {error}")
            finally:
                # Killing the Docker CLI alone does not stop a timed-out container.
                try:
                    subprocess.run(["docker", "rm", "-f", name], capture_output=True, timeout=10)
                except (OSError, subprocess.TimeoutExpired):
                    pass
