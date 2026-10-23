"""Live, paid audit evaluation. Each generated suite runs on buggy and corrected code.
Run after starting the backend. No reference source is supplied to the model.
"""
import argparse
import json
import os
import statistics
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")

def request(path, body=None):
    base = os.getenv("BENCHMARK_API_URL", "http://127.0.0.1:8000").rstrip("/")
    req = urllib.request.Request(base + path, data=json.dumps(body).encode() if body is not None else None,
        headers={"Content-Type": "application/json", "X-Arena-Token": os.getenv("AGENTARENA_API_TOKEN", "")})
    with urllib.request.urlopen(req, timeout=600) as response:
        return json.load(response)

def evaluate(report):
    reference = report.get("reference_validation") or {}
    failures = report.get("failures") or []
    assertion = any(f.get("category") == "ASSERTION_FAILURE" for f in failures)
    ref_tests = {t["name"]: t for t in reference.get("tests", [])}
    witnessed = [f["test_name"] for f in failures if f.get("category") == "ASSERTION_FAILURE" and ref_tests.get(f["test_name"], {}).get("outcome") == "passed"]
    evidence = report.get("test_evidence") or []
    # These counts measure matched excerpt provenance, not semantic support or causation.
    cited_tests = [entry.get("test_name") for entry in evidence if entry.get("sources")]
    return {"tests_with_matched_excerpts": len(cited_tests), "matched_excerpt_test_names": cited_tests,
        "known_bug_detected": bool(assertion and witnessed and reference.get("success") and report.get("status") == "REJECTED"),
            "corrected_suite_passed": reference.get("success") if reference else None,
            "witness_tests": witnessed, "inconclusive": report.get("status") == "INCONCLUSIVE"}

def run():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenario", default="all")
    parser.add_argument("--configuration", choices=["baseline", "tavily", "both"], default="both")
    parser.add_argument("--repeats", type=int, choices=range(1, 6), default=1)
    args = parser.parse_args()
    scenarios = request("/api/scenarios")["scenarios"]
    if args.scenario != "all":
        scenarios = [s for s in scenarios if s["id"] == args.scenario]
    if not scenarios:
        raise SystemExit("Unknown scenario")
    variants = [False, True] if args.configuration == "both" else [args.configuration == "tavily"]
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    output = ROOT / "benchmarks/results" / f"paired_{stamp}.json"
    rows = []
    for index in range(args.repeats):
        for scenario in scenarios:
            # Alternate ordering between repeats to reduce ordering bias.
            for research in variants[::1 if index % 2 == 0 else -1]:
                start = time.perf_counter()
                row = {"scenario": scenario["id"], "repeat": index + 1, "configuration": "tavily" if research else "baseline"}
                try:
                    report = request("/api/investigate", {"scenario_id": scenario["id"], "bug_report": scenario["default_bug_report"], "mode": "audit", "enable_research": research})
                    row.update(evaluate(report))
                    row.update({"status": report["status"], "duration_seconds": round(time.perf_counter() - start, 2), "research_status": report.get("research", {}).get("status"), "research_cached": report.get("research", {}).get("cached"), "model": report.get("model"), "model_usage": report.get("model_usage"), "report": report})
                except Exception as error:
                    row.update({"status": "ERROR", "error": str(error), "known_bug_detected": None, "corrected_suite_passed": None})
                rows.append(row)
                output.parent.mkdir(parents=True, exist_ok=True)
                output.write_text(json.dumps({"kind": "paired_live_model_evaluation", "repeats": args.repeats, "limitations": "Curated seeded scenarios; symptoms are supplied. Record research failures and cold/warm cache state; no improvement is assumed.", "results": rows}, indent=2))
                print(row["scenario"], row["configuration"], row["status"], row.get("known_bug_detected"), flush=True)
                time.sleep(max(0, 21 - (time.perf_counter() - start)))
    print(output)

if __name__ == "__main__":
    run()
