import Link from "next/link";
import pilot from "../../public/evidence/benchmark-pilot.json";
import controls from "../../public/evidence/curated-controls.json";

export const metadata = { title: "AgentArena — Evidence & benchmark" };
export default function Benchmarks() {
  const groups = ["baseline", "tavily"].map((configuration) => {
    const rows = pilot.results.filter(
      (row) => row.configuration === configuration,
    );
    return {
      configuration,
      count: rows.length,
      detected: rows.filter((row) => row.known_bug_detected).length,
      mean:
        rows.reduce((sum, row) => sum + row.duration_seconds, 0) / rows.length,
    };
  });
  return (
    <main className="benchmark-page">
      <Link className="text-button" href="/">
        ← Back to AgentArena
      </Link>
      <p className="eyebrow" style={{ marginTop: 36 }}>
        METHODS / RESULTS / LIMITATIONS
      </p>
      <h1>Evidence you can inspect.</h1>
      <p>
        AgentArena challenges generated patches with executable tests. This page
        separates recorded model results from hand-written fixture checks. A
        source citation alone never proves a defect.
      </p>
      <section className="benchmark-section">
        <p className="eyebrow">01 / SUPPLIED HISTORICAL MODEL RUNS</p>
        <h2>Four bugs. Two configurations. No demonstrated Tavily uplift.</h2>
        <p>
          Recorded October 21, 2026. We reviewed the supplied assertion output
          against each seeded defect. These historical runs were not rerun
          during this update.
        </p>
        <div className="benchmark-table">
          <table>
            <thead>
              <tr>
                <th>Configuration</th>
                <th>Cases</th>
                <th>Known bugs reproduced</th>
                <th>Mean time</th>
                <th>Corrected controls</th>
              </tr>
            </thead>
            <tbody>
              {groups.map((group) => (
                <tr key={group.configuration}>
                  <td>{group.configuration}</td>
                  <td>{group.count}</td>
                  <td>
                    {group.detected}/{group.count}
                  </td>
                  <td>{group.mean.toFixed(2)}s</td>
                  <td>Not evaluated</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <ul>
          {pilot.limitations.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
        <div className="benchmark-downloads">
          <a href="/evidence/benchmark-pilot.json" download>
            Download reviewed pilot JSON
          </a>
          <a href="/evidence/recorded-investigation.json" download>
            Download recorded investigation
          </a>
        </div>
      </section>
      <section className="benchmark-section">
        <p className="eyebrow">02 / CURATED FIXTURE SANITY CHECKS</p>
        <h2>Does each control distinguish buggy and corrected code?</h2>
        <p>
          {controls.limitations} Runner: {controls.runner}. Model calls:{" "}
          {controls.model_calls}. Tavily calls: {controls.tavily_calls}.
        </p>
        <div className="benchmark-table">
          <table>
            <thead>
              <tr>
                <th>Scenario</th>
                <th>Original tests, buggy</th>
                <th>Boundary control, buggy</th>
                <th>Boundary control, corrected</th>
                <th>Fixture check</th>
              </tr>
            </thead>
            <tbody>
              {controls.results.map((row) => (
                <tr key={row.scenario}>
                  <td>{row.scenario}</td>
                  <td>{row.buggy.original.success ? "Pass" : "Fail"}</td>
                  <td>{row.buggy.boundary.success ? "Pass" : "Fail"}</td>
                  <td>{row.corrected.boundary.success ? "Pass" : "Fail"}</td>
                  <td>
                    {row.expected_result_observed
                      ? "Expected difference observed"
                      : "Needs review"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <a
          className="text-button"
          href="/evidence/curated-controls.json"
          download
        >
          Download actual control output ↗
        </a>
      </section>
      <section className="benchmark-section">
        <p className="eyebrow">03 / DOCUMENTATION-INFORMED SECURITY REVIEW</p>
        <h2>When URL parsing and security intent disagree.</h2>
        <p>
          The new Safe Redirect Review checks a post-login redirect helper. Its
          contract requires every returned URL to remain on the application’s
          origin. Tavily searches primary Python 3.11 documentation; Nemotron
          proposes tests with source IDs and exact supporting excerpts.
        </p>
        <p>
          AgentArena verifies whether each quoted excerpt occurs in the
          retrieved source, then executes the same generated suite on both
          implementations. A quote match establishes provenance, not semantic
          correctness. A failed corrected control makes the result inconclusive.
        </p>
        <p>
          No live Nemotron/Tavily result for this new case is claimed in this
          package. Use the live workbench after configuring the backend, or run
          the paired evaluation command in the README. Model knowledge may
          already cover the issue, so an improvement over baseline is not
          assumed.
        </p>
      </section>
    </main>
  );
}
