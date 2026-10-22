import argparse
import csv
import json
import time
import urllib.error
import urllib.request

from datetime import datetime, timezone
from pathlib import Path


API_URL = "http://localhost:8000"

RESULTS_DIRECTORY = (
    Path(__file__).resolve().parent
    / "results"
)

SCENARIOS = [
    "discount",
    "authentication",
    "inventory",
    "shipping",
]


def fetch_scenarios():
    """
    Retrieve the scenario registry from AgentArena.
    """

    request = urllib.request.Request(
        f"{API_URL}/api/scenarios",
        method="GET",
    )

    with urllib.request.urlopen(
        request,
        timeout=15,
    ) as response:

        payload = json.loads(
            response.read().decode("utf-8")
        )

    return {
        scenario["id"]: scenario
        for scenario in payload["scenarios"]
    }


def investigate(
    scenario_id: str,
    bug_report: str,
    enable_research: bool,
):
    """
    Run one audit investigation through the FastAPI API.
    """

    payload = {
        "scenario_id": scenario_id,
        "bug_report": bug_report,
        "mode": "audit",
        "enable_research": enable_research,
    }

    request = urllib.request.Request(
        f"{API_URL}/api/investigate",
        data=json.dumps(
            payload
        ).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
        },
        method="POST",
    )

    start = time.perf_counter()

    with urllib.request.urlopen(
        request,
        timeout=300,
    ) as response:

        report = json.loads(
            response.read().decode("utf-8")
        )

    duration = round(
        time.perf_counter() - start,
        2,
    )

    return report, duration


def evaluate_result(
    scenario_id: str,
    report: dict,
    duration: float,
    enable_research: bool,
):
    """
    Extract observable benchmark metrics.

    A rejected verdict is not automatically counted
    as successful known-bug detection.
    """

    original = report.get(
        "original_tests"
    ) or {}

    adversarial = report.get(
        "adversarial_tests"
    ) or {}

    research = report.get(
        "research"
    ) or {}

    failures = report.get(
        "failures"
    ) or []

    assertion_failures = [
        failure
        for failure in failures
        if failure.get("category") == (
            "ASSERTION_FAILURE"
        )
    ]

    return {
        "scenario": scenario_id,
        "configuration": (
            "tavily"
            if enable_research
            else "baseline"
        ),
        "investigation_id": report.get(
            "investigation_id"
        ),
        "status": report.get(
            "status"
        ),
        "evidence_score": report.get(
            "evidence_score"
        ),
        "original_total": original.get(
            "total",
            0,
        ),
        "original_passed": original.get(
            "passed",
            0,
        ),
        "adversarial_total": adversarial.get(
            "total",
            0,
        ),
        "adversarial_passed": adversarial.get(
            "passed",
            0,
        ),
        "adversarial_failed": adversarial.get(
            "failed",
            0,
        ),
        "assertion_failure_count": len(
            assertion_failures
        ),
        "research_sources": len(
            research.get(
                "sources",
                []
            )
        ),
        "research_cached": research.get(
            "cached",
            False,
        ),
        "duration_seconds": duration,

        # We will manually confirm whether the failing
        # assertions reproduce the known scenario defect.
        "known_bug_detected": None,

        "failure_evidence": [
            {
                "test_name": failure.get(
                    "test_name"
                ),
                "category": failure.get(
                    "category"
                ),
                "evidence": failure.get(
                    "evidence"
                ),
            }
            for failure in failures
        ],
    }


def save_results(
    results: list,
    timestamp: str,
):

    RESULTS_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )

    json_path = (
        RESULTS_DIRECTORY
        / f"benchmark_{timestamp}.json"
    )

    csv_path = (
        RESULTS_DIRECTORY
        / f"benchmark_{timestamp}.csv"
    )

    json_path.write_text(
        json.dumps(
            results,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    csv_results = []

    for result in results:

        csv_result = {
            key: value
            for key, value in result.items()
            if key != "failure_evidence"
        }

        csv_results.append(
            csv_result
        )

    with csv_path.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=list(
                csv_results[0].keys()
            ),
        )

        writer.writeheader()
        writer.writerows(
            csv_results
        )

    print(
        f"\nJSON: {json_path}"
    )

    print(
        f"CSV:  {csv_path}"
    )


def main():

    parser = argparse.ArgumentParser(
        description=(
            "Benchmark AgentArena "
            "adversarial verification."
        )
    )

    parser.add_argument(
        "--scenario",
        choices=SCENARIOS + ["all"],
        default="all",
    )

    parser.add_argument(
        "--configuration",
        choices=[
            "baseline",
            "tavily",
            "both",
        ],
        default="both",
    )

    args = parser.parse_args()

    available_scenarios = fetch_scenarios()

    selected_scenarios = (
        SCENARIOS
        if args.scenario == "all"
        else [args.scenario]
    )

    configurations = (
        [False, True]
        if args.configuration == "both"
        else [
            args.configuration == "tavily"
        ]
    )

    results = []

    total_runs = (
        len(selected_scenarios)
        * len(configurations)
    )

    print(
        "\nAGENTARENA BENCHMARK"
    )

    print(
        "=" * 55
    )

    print(
        f"Planned investigations: "
        f"{total_runs}"
    )

    run_number = 0

    for scenario_id in selected_scenarios:

        scenario = available_scenarios.get(
            scenario_id
        )

        if not scenario:

            raise ValueError(
                f"Scenario unavailable: "
                f"{scenario_id}"
            )

        for enable_research in configurations:

            run_number += 1

            configuration = (
                "TAVILY"
                if enable_research
                else "BASELINE"
            )

            print(
                f"\n[{run_number}/{total_runs}] "
                f"{scenario_id.upper()} "
                f"/ {configuration}"
            )

            try:

                report, duration = investigate(
                    scenario_id=scenario_id,
                    bug_report=scenario[
                        "default_bug_report"
                    ],
                    enable_research=enable_research,
                )

                result = evaluate_result(
                    scenario_id=scenario_id,
                    report=report,
                    duration=duration,
                    enable_research=enable_research,
                )

                results.append(
                    result
                )

                print(
                    f"Status: "
                    f"{result['status']}"
                )

                print(
                    f"Original: "
                    f"{result['original_passed']}/"
                    f"{result['original_total']}"
                )

                print(
                    f"Adversarial: "
                    f"{result['adversarial_passed']}/"
                    f"{result['adversarial_total']}"
                )

                print(
                    f"Assertion failures: "
                    f"{result['assertion_failure_count']}"
                )

                print(
                    f"Duration: "
                    f"{duration}s"
                )

            except Exception as error:

                print(
                    f"BENCHMARK ERROR: "
                    f"{error}"
                )

                results.append({
                    "scenario": scenario_id,
                    "configuration": (
                        "tavily"
                        if enable_research
                        else "baseline"
                    ),
                    "investigation_id": None,
                    "status": "ERROR",
                    "evidence_score": None,
                    "original_total": 0,
                    "original_passed": 0,
                    "adversarial_total": 0,
                    "adversarial_passed": 0,
                    "adversarial_failed": 0,
                    "assertion_failure_count": 0,
                    "research_sources": 0,
                    "research_cached": False,
                    "duration_seconds": None,
                    "known_bug_detected": None,
                    "failure_evidence": [],
                })

    timestamp = datetime.now(
        timezone.utc
    ).strftime(
        "%Y%m%d_%H%M%S"
    )

    save_results(
        results,
        timestamp,
    )

    print(
        "\nBenchmark complete."
    )


if __name__ == "__main__":
    main()