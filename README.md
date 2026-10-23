# AgentArena

A fix is a claim. Make it prove itself.

AgentArena lets a coding agent attempt a small software bug in a restricted Docker workspace, then asks an independent verifier to generate adversarial tests. A verdict includes test execution, a corrected reference control, the generated suite, and research provenance. It belongs in the Coding and Agentic Engineering track.

## What the verdict means

- **PASSED_CHECKS**: the observed tests passed. This is not a guarantee of correctness or a probability of safety.
- **REJECTED**: an executable assertion exposed a failure and the same generated suite passed on the curated corrected reference.
- **INCONCLUSIVE**: missing tests, collection/runtime errors, skipped checks, or an invalid reference control prevent a supported verdict.

Corrected references are withheld from agent workspaces. Test scores are descriptive pass rates, not calibrated confidence. Tool actions are observable traces; they do not reveal or verify a model’s private reasoning.

## Run locally

Use Python 3.11+, Node 20.9+, and a running Docker daemon.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
docker build -t agentarena-sandbox backend/sandbox
```

Edit `.env`: supply your Nebius Token Factory key, NVIDIA model name, optional Tavily key, and a strong `AGENTARENA_API_TOKEN`. Generate the token locally with `python -c "import secrets; print(secrets.token_urlsafe(32))"`.

```bash
python -m uvicorn backend.api:app --host 127.0.0.1 --port 8000 --workers 1
```

In another terminal:

```bash
cd frontend
cp .env.example .env.local
npm ci
npm run dev
```

Put the same API token in `frontend/.env.local`, alongside `BACKEND_URL=http://127.0.0.1:8000`. Neither variable should use a `NEXT_PUBLIC_` prefix. Open http://localhost:3000. The frontend proxies backend traffic and keeps the token server-side.

## Hosted demo

Vercel hosts `frontend/`. Docker execution needs a separate always-on Linux host. See [deployment instructions](deploy/README.md). A clearly labelled recorded investigation and evidence page remain available if live execution is offline. Recorded results are never presented as newly executed runs.

## Tavily: evidence that can be checked

The new Safe Redirect Review scenario investigates a post-login redirect. Tavily retrieves version-matched Python 3.11 documentation about URL joining. The verifier proposes tests with source IDs and exact excerpts; the server checks excerpts against retrieved text and links each generated test to its evidence. Matching an excerpt establishes text provenance, not semantic correctness. The same suite must also pass on a withheld corrected implementation.

This makes the demonstration concrete: document → security boundary → generated test → executable failure → corrected control. Research can be switched off for a comparison. Retrieval errors are visible, cached results are labelled, and caches expire after 24 hours. No API key means research is disabled, not simulated.

## Evidence and benchmarks

`/benchmarks` separates two kinds of evidence:

1. **Historical pilot:** your supplied eight runs, four cases with and without Tavily. Both detected all four seeded bugs on manual assertion review. Tavily runs used cached research and averaged 17.33 seconds versus 14.91 seconds without it. Those runs did not include corrected controls and do not demonstrate an improvement from Tavily.
2. **Curated controls:** six developer-written fixture checks reproduced each seeded boundary failure and passed the corrected implementations. These are implementation sanity checks, not AI benchmark results; they make zero model or search calls.

Run inexpensive checks:

```bash
python -m pytest -q
python benchmarks/check_controls.py
# Use the production container runner once Docker is installed:
python benchmarks/check_controls.py --docker
cd frontend
npm run lint
npm run build
```

Run a real paid benchmark only after configuring credentials and starting the backend:

```bash
python benchmarks/run_benchmark.py --scenario all --configuration both --repeats 1
```

It runs twelve jobs and records per-run evidence, corrected controls, research status, usage, and failures. Repeat comparisons before claiming Tavily improves detection. API limits apply. Review the CLI help for options.

## Runtime boundaries

Containers use read-only source mounts, no network, a non-root user, dropped capabilities, process/memory/CPU limits, and forced cleanup after timeouts. The coding agent may edit only the scenario’s production source file. This is a hackathon sandbox, not a hardened multi-tenant execution service.

A private API token, one active job, and configurable daily/minute limits bound public demo use. Limits are in memory and reset on process restart; use one backend worker. They are not a billing cap. Configure provider spending limits separately. Long runs can outlive hosting request limits; successful completed reports persist in backend history. Store `data/` on persistent disk and never put keys into Git.

## Submission checklist

The app uses an NVIDIA Nemotron model via the Nebius OpenAI-compatible endpoint. Confirm the configured model is available in your account, test a real hosted run, publish the repository with its MIT license, and record a public video under three minutes. Demonstrate the actual Nebius model and actual Tavily retrieval. Explain the historical pilot’s limitations rather than claiming a measured uplift that has not been shown.


## Callback documentation case

Select **Callback Query Review**. The symptom report mentions reconciliation failures and optional metadata but does not name the parsing option or a failing input. The source contract requires retaining submitted form fields; only the buggy helper and original tests are supplied to Nemotron. The corrected reference stays outside its workspace.

Tavily searches Python 3.11 documentation and, if necessary, extracts the exact library page. Task-specific passage selection is curated, not blind discovery. We check matched excerpts for provenance; a reviewer must still judge whether a quote supports the test. The model may already know this behavior. No detection improvement is claimed until the paired results support it.

After local checks, a first comparison costs two live investigations:

```bash
python benchmarks/run_benchmark.py --scenario callback --configuration both --repeats 1
```

The JSON under benchmarks/results retains both complete reports, failures, research cache state and matched-excerpt counts. Do not cherry-pick successful runs. One pair is a smoke test, not a measured advantage. If it is informative and credits permit, use repeats 3 for six runs with alternating order. Preserve errors and ties. Cached Tavily context is still labelled; a cold retrieval must be demonstrated separately if all comparisons use the cache.

For the video, show the original suite passing, a behavior-specific documentation excerpt, the generated assertion, its failure on the buggy helper and its success on the withheld reference. If research-off catches the same bug, say so. This fixture is seeded and curated; it is not a real payment integration or a signature verifier.


## Audit your own Python code

Set `ENABLE_CUSTOM_AUDIT=true` in the backend `.env` and restart the backend. The UI uses the health capability flag to enable **Your Python code**. Once deployed and enabled on that backend, visitors can use this form; they do not need to select a fixture. Keep the private proxy token and global demo budgets configured. Disable the flag to stop custom submissions.

Paste one module (up to 20,000 characters), explain expected behavior, and optionally paste pytest tests (up to 12,000 characters, importing from `solution`). This workflow supports audit only, standard library plus pytest, and no package installation. Without existing tests, the original check imports the module; it is labelled an import smoke check, not a complete baseline suite.

User code is parsed as text by the API and executed only by the existing restricted Docker runner. Code and requirements are sent to Nebius for test generation. Tavily is disabled for arbitrary custom inputs in this version. The temporary workspace is removed after completion. Custom reports are returned to that browser session, never written to shared investigation history or latest_report.json; users can download JSON before leaving. Provider retention policies still apply to inference requests.

There is no corrected reference for arbitrary code. Custom reports retain status INCONCLUSIVE and no numeric score, with a separate assessment: failures reproduced, checks passed (unvalidated), or inconclusive execution. A reproduced failure must still be reviewed against the supplied requirements. These results do not certify code correctness or safety. Curated scenario verdicts continue to use their withheld reference checks.

This is a limited hackathon feature for a controlled Docker host, not a hardened multi-tenant arbitrary-code execution service. Do not expose the Docker socket, mount host credentials into a sandbox, or treat user-generated test reports as a security boundary.

Free checks before a live custom audit:

```bash
python -m pytest tests/test_custom_audit.py -q
```

A small live example: paste `def add(a, b): return a - b`, require addition, and click **Audit my code**. Review the generated tests and download the report. This is a paid model request. The delivery's browser demonstration uses a clearly labelled local UI fixture, not a live Nebius result.
