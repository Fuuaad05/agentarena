# AgentArena

**Don't trust a patch. Verify it.**

AgentArena is an AI-powered code investigation and adversarial verification system built for the Nebius × NVIDIA Global AI Hackathon 2026.

It uses NVIDIA Nemotron through Nebius Token Factory to investigate reported software defects, generate adversarial tests, and evaluate implementations using executable evidence.

## Features

- Autonomous Repair: Investigates bugs, proposes patches, and verifies them.
- Adversarial Audit: Tests existing implementations without modifying source code.
- NVIDIA Nemotron coding and verification agents.
- Tavily-assisted technical research with source references.
- Docker-isolated pytest execution.
- Real-time investigation progress through SSE.
- Test pass scoring and failure classification.
- Git-style patch diffs.
- Persistent investigation history.
- Four built-in Python scenarios.

## Architecture

Next.js frontend → FastAPI backend → Nemotron / Tavily → Docker pytest sandbox → Evidence report.

## Built-in Scenarios

| Scenario | Known defect |
|---|---|
| Discount Service | Zero-percent discounts incorrectly return zero |
| Authentication Service | Sessions remain valid at their exact expiration |
| Inventory Service | Exact-stock orders are rejected |
| Shipping Calculator | Exactly 1 kg is charged at the wrong tier |

The scenarios intentionally contain seeded defects. Their original tests omit the known failing boundary cases.

## Benchmark

In a single controlled pilot:

- 13/13 original tests passed.
- Four seeded defects were reproduced using Nemotron-generated adversarial tests.
- Detection was 4/4 with and without Tavily.
- Tavily provided external research context, but no detection-rate improvement was established.

The bug reports described the observed problems. This evaluates reproduction and adversarial test generation, not blind discovery of unknown defects.

Results: `benchmarks/results/benchmark_20261021_210530.json`.

## Tech Stack

- NVIDIA Nemotron via Nebius Token Factory
- Tavily Search API
- Python / FastAPI
- Docker / pytest
- Next.js / TypeScript
- SQLite

## Local Development

### Backend

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt