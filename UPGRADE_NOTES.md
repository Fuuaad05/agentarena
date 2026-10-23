# What changed

- Added a Safe Redirect Review scenario and withheld corrected references for all five scenarios.
- Validated generated suites against corrected controls; collection errors, invalid controls, skipped/missing tests and non-assertion failures yield INCONCLUSIVE.
- Added per-test research provenance, exact-excerpt validation, version-matched redirect documentation queries and a 24-hour research cache.
- Restricted agent edits to the production file; tightened Docker isolation and timeout cleanup.
- Added private run authorization, one concurrent job, minute/day limits, a server-side Next.js proxy and real dependency readiness.
- Added labelled recorded playback, a benchmark evidence page, optional research, generated tests, reference results and observable action traces.
- Preserved the warm white/ink visual direction, repaired the font stack and added responsive evidence layouts.
- Replaced the incomplete README, added VM/Vercel deployment instructions, minimal pinned Python dependencies and focused automated checks.

The historical pilot shows no measured Tavily advantage. New fixture checks use handwritten tests and do not establish AI performance. Run the real controlled benchmark before making stronger claims.

## Installing this copy

Back up your existing project, extract the project folder, and open it in VS Code. Keep your existing private `.env` values locally and apply the new example settings. Install dependencies again. Configure the same private API token in the backend and Vercel, and configure Vercel’s server-side BACKEND_URL. No secrets are included in this ZIP.

## Verification

See README for the focused test suite, curated controls, frontend lint/build and optional Docker checks. The delivery message records which checks were actually run. Live Nebius/Tavily and Docker execution require your configured host; they are not represented by local fixture checks.
