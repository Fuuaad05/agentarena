import difflib
import json
import hashlib
import tempfile
import shutil

from datetime import datetime, timezone
from pathlib import Path

from backend.agents.coding_agent import CodingAgent
from backend.agents.verifier import AdversarialVerifier

from backend.database.storage import save_investigation, DATABASE_PATH
from backend.events import EventEmitter

from backend.research.tavily_research import TavilyResearch
from backend.research.evidence import build_test_evidence

from backend.sandbox.docker_runner import DockerSandbox

from backend.scenarios import Scenario

from backend.scoring.trust_engine import (
    TrustEngine,
    TestResults,
)

from backend.verification.classifier import FailureClassifier


class AgentArenaPipeline:
    """
    AgentArena autonomous verification pipeline.

    Workflow:
    1. Coding agent investigates and fixes a bug,
       or audit mode preserves the original source.
    2. Docker executes original tests.
    3. Tavily researches relevant edge cases.
    4. Nemotron generates adversarial tests.
    5. Docker executes adversarial tests.
    6. Trust Engine calculates an evidence score.
    7. Results are stored in SQLite.
    """

    def __init__(
        self,
        repo_path: str,
        event_callback=None,
        scenario: Scenario | None = None,
        enable_research: bool = True,
    ):

        self.repo_path = Path(
            repo_path
        ).resolve()

        if not self.repo_path.is_dir():

            raise ValueError(
                f"Repository does not exist: "
                f"{self.repo_path}"
            )

        self.scenario = scenario

        self.enable_research = enable_research

        self.events = EventEmitter(
            event_callback
        )

        self.sandbox = DockerSandbox(
            str(self.repo_path)
        )

    def emit(
        self,
        stage: str,
        status: str,
        message: str,
    ):

        self.events.emit(
            stage,
            status,
            message,
        )

    def convert_results(
        self,
        result: dict,
    ) -> TestResults:

        summary = result.get(
            "summary",
            {},
        )

        return TestResults(
            total=summary.get(
                "total",
                0,
            ),
            passed=summary.get(
                "passed",
                0,
            ),
            failed=summary.get(
                "failed",
                0,
            ),
            errors=summary.get(
                "error",
                0,
            ),
        )

    def save_report(
        self,
        report: dict,
    ) -> dict:

        report["events"] = list(self.events.history)
        investigation_id = save_investigation(
            report
        )

        report["investigation_id"] = (
            investigation_id
        )

        report_path = DATABASE_PATH.parent / "latest_report.json"

        report_path.write_text(
            json.dumps(
                report,
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

        return report

    def run(
        self,
        bug_report: str,
        mode: str = "repair",
    ) -> dict:

        if mode not in (
            "repair",
            "audit",
        ):

            raise ValueError(
                f"Unsupported investigation mode: {mode}"
            )

        timestamp = datetime.now(
            timezone.utc
        ).isoformat()

        scenario_id = (
            self.scenario.id
            if self.scenario
            else "discount"
        )

        source_filename = (
            self.scenario.source_file
            if self.scenario
            else "shop.py"
        )

        test_filename = (
            self.scenario.test_file
            if self.scenario
            else "test_shop.py"
        )

        test_imports = (
            self.scenario.test_imports
            if self.scenario
            else (
                "from shop import "
                "calculate_discount"
            )
        )

        source_path = (
            self.repo_path
            / source_filename
        )

        original_test_path = (
            self.repo_path
            / test_filename
        )

        adversarial_path = (
            self.repo_path
            / "test_adversarial.py"
        )

        if not source_path.is_file():

            raise FileNotFoundError(
                f"Source file not found: "
                f"{source_filename}"
            )

        if not original_test_path.is_file():

            raise FileNotFoundError(
                f"Test file not found: "
                f"{test_filename}"
            )

        if adversarial_path.exists():
            adversarial_path.unlink()

        original_test_hash = hashlib.sha256(original_test_path.read_bytes()).hexdigest()

        original_source = (
            source_path.read_text(
                encoding="utf-8"
            )
        )

        print(
            "\n" + "=" * 55
        )

        print(
            "AGENTARENA - AUTONOMOUS VERIFICATION"
        )

        print(
            "=" * 55
        )

        self.emit(
            "investigation",
            "running",
            (
                "Investigation started: "
                f"{scenario_id}"
            ),
        )

        # ======================================
        # STEP 1: CODING AGENT / AUDIT MODE
        # ======================================

        if mode == "repair":

            self.emit(
                "coding",
                "running",
                (
                    "NVIDIA Nemotron is "
                    "investigating the repository"
                ),
            )

            coding_agent = CodingAgent(
                repo_path=str(
                    self.repo_path
                ),
                max_steps=12,
                allowed_files={source_filename},
            )

            coding_summary = (
                coding_agent.run(
                    bug_report
                )
            )

            self.emit(
                "coding",
                "completed",
                (
                    "Coding agent finished "
                    "its investigation"
                ),
            )

        else:

            coding_summary = (
                "Adversarial Audit Mode: "
                "Source code was not modified."
            )

            self.emit(
                "coding",
                "completed",
                (
                    "Audit mode selected: "
                    "skipping code modification"
                ),
            )

        modified_source = (
            source_path.read_text(
                encoding="utf-8"
            )
        )

        patch_diff = "".join(
            difflib.unified_diff(
                original_source.splitlines(
                    keepends=True
                ),
                modified_source.splitlines(
                    keepends=True
                ),
                fromfile=(
                    f"a/{source_filename}"
                ),
                tofile=(
                    f"b/{source_filename}"
                ),
            )
        )

        # ======================================
        # STEP 2: ORIGINAL TESTS
        # ======================================

        self.emit(
            "original_tests",
            "running",
            (
                "Running original tests "
                "inside Docker"
            ),
        )

        if hashlib.sha256(original_test_path.read_bytes()).hexdigest() != original_test_hash:
            raise RuntimeError("Original tests were modified; investigation refused.")
        original_result = (
            self.sandbox.run_tests(
                test_file=test_filename
            )
        )

        original_summary = (
            original_result.get(
                "summary",
                {},
            )
        )

        self.emit(
            "original_tests",
            (
                "completed"
                if original_result.get(
                    "success"
                )
                else "failed"
            ),
            (
                f"Original tests: "
                f"{original_summary.get('passed', 0)}/"
                f"{original_summary.get('total', 0)} "
                f"passed"
            ),
        )

        if (original_result.get("execution_error") or original_summary.get("error", 0)
                or original_summary.get("total", 0) <= 0):
            diagnostic = original_result.get("execution_error") or original_result.get("output") or "No usable original test report."
            self.emit("original_tests", "failed", str(diagnostic)[-2000:])
            self.emit("investigation", "failed", "Stopped before paid research/model calls: original tests could not execute.")
            return self.save_report({
                "project": "AgentArena", "version": "1.0", "timestamp": timestamp,
                "scenario_id": scenario_id, "bug_report": bug_report, "mode": mode,
                "coding_summary": coding_summary, "patch_diff": patch_diff,
                "original_tests": original_summary, "adversarial_tests": None,
                "status": "INCONCLUSIVE", "evidence_score": None,
                "explanation": "Original test execution failed; verification was stopped before research and verifier calls. " + str(diagnostic)[-2000:],
                "error": str(diagnostic)[-12000:], "execution": {"original": original_result},
                "research": {"enabled": False, "status": "not_run", "sources": [], "cached": False},
            })

        # ======================================
        # STEP 3: TAVILY RESEARCH
        # ======================================

        research = {
            "enabled": False,
            "status": "disabled",
            "query": "",
            "sources": [],
            "context": "",
            "cached": False,
            "error": None,
        }

        if self.enable_research:

            self.emit(
                "research",
                "running",
                (
                    "Researching relevant "
                    "edge cases with Tavily"
                ),
            )

            try:

                research_service = (
                    TavilyResearch()
                )

                research = (
                    research_service.search(
                        scenario_id=scenario_id,
                        bug_report=bug_report,
                    )
                )

                if research["status"] == (
                    "completed"
                ):

                    source_count = len(
                        research["sources"]
                    )

                    cache_message = (
                        " (cached)"
                        if research.get(
                            "cached"
                        )
                        else ""
                    )

                    self.emit(
                        "research",
                        "completed",
                        (
                            f"Tavily found "
                            f"{source_count} "
                            f"research sources"
                            f"{cache_message}"
                        ),
                    )

                else:

                    self.emit(
                        "research",
                        "completed",
                        (
                            "Research unavailable; "
                            "continuing with "
                            "repository evidence"
                        ),
                    )

            except Exception as error:

                research = {
                    "enabled": True,
                    "status": "failed",
                    "query": "",
                    "sources": [],
                    "context": "",
                    "cached": False,
                    "error": str(error),
                }

                self.emit(
                    "research",
                    "failed",
                    (
                        "Research failed; "
                        "continuing without it"
                    ),
                )

        # ======================================
        # STEP 4: ADVERSARIAL VERIFIER
        # ======================================

        self.emit(
            "adversarial",
            "running",
            (
                "Nemotron is generating "
                "adversarial tests"
            ),
        )

        try:

            source_code = (
                source_path.read_text(
                    encoding="utf-8"
                )
            )

            existing_tests = (
                original_test_path.read_text(
                    encoding="utf-8"
                )
            )

            verifier = (
                AdversarialVerifier()
            )

            verifier.progress_callback = lambda message: self.emit("adversarial", "running", message)
            verification = (
                verifier.generate_tests(
                    bug_report=bug_report,
                    source_code=source_code,
                    existing_tests=existing_tests,
                    test_imports=test_imports,
                    research_context=(
                        research.get(
                            "context",
                            "",
                        )
                    ),
                )
            )

            generated_tests = (
                verification.get(
                    "tests",
                    [],
                )
            )

            if not generated_tests:

                raise ValueError(
                    "Verifier generated no tests."
                )

            test_content = (
                "import pytest\n"
                f"{test_imports}\n\n"
            )

            for test in generated_tests:

                test_content += (
                    test["code"]
                    + "\n\n"
                )

            adversarial_path.write_text(
                test_content,
                encoding="utf-8",
            )

            self.emit(
                "adversarial",
                "completed",
                (
                    f"Generated "
                    f"{len(generated_tests)} "
                    f"adversarial tests"
                ),
            )

        except Exception as error:

            self.emit(
                "adversarial",
                "failed",
                (
                    f"Verifier failed: "
                    f"{error}"
                ),
            )

            failure_report = {
                "project": "AgentArena",
                "version": "1.0",
                "timestamp": timestamp,
                "scenario_id": scenario_id,
                "bug_report": bug_report,
                "coding_summary": coding_summary,
                "patch_diff": patch_diff,
                "original_tests": original_summary,
                "adversarial_tests": None,
                "evidence_score": None,
                "status": "INCONCLUSIVE",
                "explanation": (
                    "Adversarial verification "
                    "could not be completed."
                ),
                "research": {
                    "enabled": research.get(
                        "enabled",
                        False,
                    ),
                    "status": research.get(
                        "status",
                        "unknown",
                    ),
                    "query": research.get(
                        "query",
                        "",
                    ),
                    "sources": research.get(
                        "sources",
                        [],
                    ),
                    "cached": research.get(
                        "cached",
                        False,
                    ),
                    "error": research.get(
                        "error"
                    ),
                },
                "mode": mode,
                "error": str(error),
                "execution": {"original": original_result},
            }

            return self.save_report(
                failure_report
            )

        # ======================================
        # STEP 5: ADVERSARIAL TEST EXECUTION
        # ======================================

        self.emit(
            "verification",
            "running",
            (
                "Executing adversarial "
                "tests inside Docker"
            ),
        )

        adversarial_result = (
            self.sandbox.run_tests(
                test_file=(
                    "test_adversarial.py"
                )
            )
        )

        classifier = (
            FailureClassifier(production_files={source_filename, str(source_path)})
        )

        classified_failures = []

        for test in (
            adversarial_result.get(
                "tests",
                [],
            )
        ):

            if test.get(
                "outcome"
            ) == "passed":
                continue

            classified = (
                classifier.classify(
                    test
                )
            )

            classified_failures.append({
                "test_name": (
                    classified.test_name
                ),
                "category": (
                    classified.category.value
                ),
                "explanation": (
                    classified.explanation
                ),
                "evidence": (
                    classified.evidence
                ),
            })

        adversarial_summary = (
            adversarial_result.get(
                "summary",
                {},
            )
        )

        self.emit(
            "verification",
            (
                "completed"
                if adversarial_result.get(
                    "success"
                )
                else "failed"
            ),
            (
                f"Adversarial tests: "
                f"{adversarial_summary.get('passed', 0)}/"
                f"{adversarial_summary.get('total', 0)} "
                f"passed"
            ),
        )

        # ======================================
        # STEP 6: TRUST ENGINE
        # ======================================

        self.emit(
            "scoring",
            "running",
            "Calculating evidence score",
        )

        # Run the *same generated suite* against the curated corrected implementation.
        # The reference lives outside the agent workspace and is never included in prompts.
        reference_validation = None
        validation_problem = None
        if self.scenario and self.scenario.reference_file and self.scenario.reference_file.is_file():
            with tempfile.TemporaryDirectory(prefix="arena_reference_") as ref_dir:
                ref_repo = Path(ref_dir) / "repository"
                shutil.copytree(self.repo_path, ref_repo)
                (ref_repo / source_filename).write_text(self.scenario.reference_file.read_text())
                self.emit("reference", "running", "Checking the generated tests against a curated corrected control")
                reference_validation = DockerSandbox(str(ref_repo)).run_tests(test_file="test_adversarial.py")
                reference_validation["kind"] = "curated_corrected_control"
                if not reference_validation.get("success") or reference_validation.get("summary", {}).get("skipped", 0):
                    validation_problem = "The generated suite did not pass the curated corrected control; its expectations or execution need review."
                self.emit("reference", "completed" if not validation_problem else "failed", "Corrected control passed" if not validation_problem else validation_problem)
        else:
            validation_problem = "No corrected reference control is available for this scenario."
        # A witness may be an assertion or a structured call-phase exception
        # traced to the known production source. Both require a passing reference.
        supported_categories = {"ASSERTION_FAILURE", "PRODUCTION_EXCEPTION"}
        unclassified_failures = [f for f in classified_failures if f["category"] not in supported_categories]
        supported_failures = [f for f in classified_failures if f["category"] in supported_categories]
        verification_warnings = []
        if unclassified_failures:
            verification_warnings.append("Some failures need manual classification. Any rejection is supported by a validated assertion or production exception, not by these unclassified failures.")
            if not supported_failures and not validation_problem:
                validation_problem = "No supported assertion or production-exception witness is available; these failures need manual review."

        trust_engine = (
            TrustEngine()
        )

        trust_report = trust_engine.calculate(
            original=self.convert_results(original_result),
            adversarial=self.convert_results(adversarial_result),
            mode=mode,
            validation_problem=validation_problem,
        )

        # ======================================
        # STEP 7: FINAL REPORT
        # ======================================

        research_report = {
            "enabled": research.get(
                "enabled",
                False,
            ),
            "status": research.get(
                "status",
                "unknown",
            ),
            "query": research.get(
                "query",
                "",
            ),
            "sources": research.get(
                "sources",
                [],
            ),
            "cached": research.get(
                "cached",
                False,
            ),
            "error": research.get(
                "error"
            ),
            "insights": (
                verification.get(
                    "research_insights",
                    [],
                )
            ),
        }

        final_report = {
            "project": "AgentArena",
            "version": "1.0",
            "timestamp": timestamp,
            "scenario_id": scenario_id,
            "bug_report": bug_report,
            "coding_summary": coding_summary,
            "patch_diff": patch_diff,
            "verifier_analysis": (
                verification.get(
                    "analysis",
                    "",
                )
            ),
            "original_tests": (
                original_summary
            ),
            "adversarial_tests": (
                adversarial_summary
            ),
            "evidence_score": (
                trust_report.score
            ),
            "status": (
                trust_report.status.value
            ),
            "explanation": (
                trust_report.explanation + (
                    " Additional unclassified failures need manual review; this rejection is supported by a validated failure witness and corrected control."
                    if verification_warnings and trust_report.status.value == "REJECTED" else ""
                )
            ),
            "failures": (
                classified_failures
            ),
            "research": research_report,
            "agent_trace": coding_agent.trace if mode == "repair" else [],
            "generated_test_source": test_content,
            "test_evidence": build_test_evidence(generated_tests, research_report["sources"], bug_report),
            "reference_validation": reference_validation,
            "execution": {"original": original_result, "adversarial": adversarial_result},
            "model": verifier.llm.model,
            "model_usage": {"verifier": verifier.llm.usage, "coding_agent": coding_agent.llm.usage if mode == "repair" else None},
            "verification_warnings": verification_warnings,
            "verification_limits": "Curated scenario; reference checks reduce false positives but do not prove arbitrary code secure.",
            "mode": mode,
        }

        final_report = (
            self.save_report(
                final_report
            )
        )

        self.emit(
            "investigation",
            "completed",
            (
                "Investigation finished: "
                f"{trust_report.status.value}"
            ),
        )

        print(
            "\n" + "=" * 55
        )

        print(
            "AGENTARENA FINAL REPORT"
        )

        print(
            "=" * 55
        )

        print(
            f"Scenario: {scenario_id}"
        )

        print(
            f"Status: "
            f"{trust_report.status.value}"
        )

        print(
            f"Evidence Score: "
            f"{trust_report.score}/100"
        )

        print(
            f"Original Tests: "
            f"{original_summary.get('passed', 0)}/"
            f"{original_summary.get('total', 0)}"
        )

        print(
            f"Adversarial Tests: "
            f"{adversarial_summary.get('passed', 0)}/"
            f"{adversarial_summary.get('total', 0)}"
        )

        print(
            f"Research Status: "
            f"{research_report['status']}"
        )

        print(
            f"Research Sources: "
            f"{len(research_report['sources'])}"
        )

        print(
            "\nReport saved successfully."
        )

        return final_report