"use client";

import { useCallback, useEffect, useState } from "react";

import Link from "next/link";

import DiffViewer from "@/components/DiffViewer";

import {
  ArrowUpRight,
  ArrowDown,
  ArrowRight,
  BookOpen,
  Check,
  ChevronRight,
  Circle,
  FileCode2,
  FlaskConical,
  GitBranch,
  Loader2,
  Play,
  RotateCw,
  Terminal,
  TriangleAlert,
} from "lucide-react";

/* =====================================================
   TYPES
===================================================== */

type HealthStatus = {
  ready?: boolean;
  features?: { custom_audit?: boolean };
  status: string;
  ai_provider: string;
  model_family: string;
  sandbox: string;
};

type TestSummary = {
  total: number;
  passed: number;
  failed: number;
  error: number;
};

type Failure = {
  test_name: string;
  category: string;
  explanation: string;
  evidence: string;
};

type ResearchSource = {
  title: string;
  url: string;
  content: string;
};

type ResearchReport = {
  enabled: boolean;
  status: string;
  query: string;
  sources: ResearchSource[];
  cached: boolean;
  error: string | null;
  insights?: string[];
};

type InvestigationReport = {
  project: string;
  version: string;
  timestamp: string;
  bug_report: string;
  investigation_id?: number;
  scenario_id?: string;
  mode?: "repair" | "audit";

  coding_summary?: string;
  verifier_analysis?: string;
  patch_diff?: string;

  original_tests?: TestSummary;
  adversarial_tests?: TestSummary | null;

  evidence_score: number | null;

  status: "PASSED_CHECKS" | "REJECTED" | "INCONCLUSIVE";

  explanation?: string;
  failures?: Failure[];
  research?: ResearchReport;
  recorded_example?: boolean;
  custom_audit?: boolean;
  assessment?: "failures_reproduced" | "checks_passed" | "inconclusive";
  original_tests_label?: string;
  agent_trace?: {
    step: number;
    tool: string;
    path?: string;
    result_excerpt: string;
  }[];
  model?: string;
  generated_test_source?: string;
  reference_validation?: {
    success: boolean;
    summary: TestSummary;
    kind: string;
  };
  test_evidence?: {
    test_name: string;
    rationale: string;
    expected_behavior: string;
    provenance_status: string;
    specification_refs?: { quote: string; verification: string }[];
    citation_checks?: { source_id: string; claimed_quote: string; status: string; reason: string }[];
    sources: {
      source_id: string;
      title: string;
      url: string;
      quote: string;
      verification: string;
    }[];
  }[];
  error?: string;
  events?: ProgressEvent[];
};

type ProgressEvent = {
  stage: string;
  status: string;
  message: string;
  timestamp: string;
};

type StreamPayload =
  | {
      type: "progress";
      data: ProgressEvent;
    }
  | {
      type: "complete";
      data: InvestigationReport;
    }
  | {
      type: "error";
      data: {
        message: string;
      };
    };

type InvestigationHistoryItem = {
  id: number;
  created_at: string;
  status: string;
  evidence_score: number | null;
  bug_report: string;
};

type Scenario = {
  id: string;
  name: string;
  description: string;
  default_bug_report: string;
};

type InvestigationMode = "repair" | "audit";

type View = "workspace" | "history";

/* =====================================================
   CONFIG
===================================================== */

// Same-origin proxy keeps backend credentials server-side, including on Vercel.
const API_URL = "/api/backend";

/* =====================================================
   HELPERS
===================================================== */

function statusClass(status: string) {
  return status === "PASSED_CHECKS"
    ? "pass"
    : status === "REJECTED"
      ? "fail"
      : "pending";
}

function formatDate(date: string) {
  return new Date(date).toLocaleString();
}

function statusLabel(status: string) {
  if (status === "PASSED_CHECKS") {
    return "Passed checks";
  }

  if (status === "REJECTED") {
    return "Potential defect";
  }

  return "Inconclusive";
}

/* =====================================================
   MAIN APPLICATION
===================================================== */

export default function Home() {
  const [health, setHealth] = useState<HealthStatus | null>(null);

  const [loading, setLoading] = useState(false);

  const [report, setReport] = useState<InvestigationReport | null>(null);

  const [error, setError] = useState<string | null>(null);

  const [events, setEvents] = useState<ProgressEvent[]>([]);

  const [history, setHistory] = useState<InvestigationHistoryItem[]>([]);

  const [scenarios, setScenarios] = useState<Scenario[]>([]);

  const [selectedScenario, setSelectedScenario] = useState("custom");

  const [mode, setMode] = useState<InvestigationMode>("audit");
  const [enableResearch, setEnableResearch] = useState(true);
  const [sourceCode, setSourceCode] = useState("");
  const [existingTests, setExistingTests] = useState("");
  const isCustom = selectedScenario === "custom";

  const [bugReport, setBugReport] = useState(
    "",
  );

  const [view, setView] = useState<View>("workspace");

  const [connectionState, setConnectionState] = useState<
    "checking" | "online" | "offline"
  >("checking");
  const [connectionAttempt, setConnectionAttempt] = useState(0);
  const [historyError, setHistoryError] = useState<string | null>(null);

  /* =====================================================
     FETCH HISTORY
  ===================================================== */

  const fetchHistory = useCallback(async () => {
    try {
      const response = await fetch(`${API_URL}/api/investigations`, {
        cache: "no-store",
      });

      if (!response.ok) {
        throw new Error("Failed to load investigations");
      }

      const data: {
        investigations: InvestigationHistoryItem[];
      } = await response.json();

      setHistory(data.investigations);
      setHistoryError(null);
    } catch (err) {
      setHistoryError(
        err instanceof Error ? err.message : "Could not load history.",
      );
    }
  }, []);

  /* =====================================================
     INITIALIZATION
  ===================================================== */

  useEffect(() => {
    let cancelled = false;

    async function initialize() {
      setConnectionState("checking");
      try {
        if (!API_URL)
          throw new Error(
            "Set NEXT_PUBLIC_API_URL to your deployed backend URL, then redeploy the frontend.",
          );
        const [healthResponse, historyResponse, scenariosResponse] =
          await Promise.all([
            fetch(`${API_URL}/api/health`, {
              signal: AbortSignal.timeout(40000),
            }),

            fetch(`${API_URL}/api/investigations`, {
              cache: "no-store",
              signal: AbortSignal.timeout(40000),
            }),

            fetch(`${API_URL}/api/scenarios`, {
              signal: AbortSignal.timeout(40000),
            }),
          ]);

        if (!healthResponse.ok) {
          throw new Error("Backend unavailable");
        }

        const healthData: HealthStatus = await healthResponse.json();

        if (!cancelled) {
          setHealth(healthData.ready === false ? null : healthData);
          setConnectionState(healthData.ready === false ? "offline" : "online");
        }

        if (historyResponse.ok) {
          const historyData: {
            investigations: InvestigationHistoryItem[];
          } = await historyResponse.json();

          if (!cancelled) {
            setHistory(historyData.investigations);
          }
        }

        if (scenariosResponse.ok) {
          const scenariosData: {
            scenarios: Scenario[];
          } = await scenariosResponse.json();

          if (!cancelled) {
            setScenarios(scenariosData.scenarios);
          }
        }
      } catch (err) {
        console.error("Initialization failed:", err);

        if (!cancelled) {
          setHealth(null);
          setConnectionState("offline");
        }
      }
    }

    void initialize();

    return () => {
      cancelled = true;
    };
  }, [connectionAttempt]);

  /* =====================================================
     INVESTIGATION
  ===================================================== */

  const handleInvestigation = async () => {
    if (loading || !bugReport.trim() || !health || health.ready === false || scenarios.length === 0 || (isCustom && (!sourceCode.trim() || !health.features?.custom_audit))) {
      return;
    }

    setLoading(true);
    setError(null);
    setReport(null);
    setEvents([]);
    setView("workspace");

    try {
      const response = await fetch(`${API_URL}/api/investigate/stream`, {
        method: "POST",

        headers: {
          "Content-Type": "application/json",
        },

        body: JSON.stringify({
          scenario_id: selectedScenario,
          bug_report: bugReport.trim(),
          mode: isCustom ? "audit" : mode,
          enable_research: isCustom ? false : enableResearch,
          ...(isCustom ? { source_code: sourceCode, existing_tests: existingTests } : {}),
        }),
      });

      if (!response.ok || !response.body) {
        const failure = await response.json().catch(() => null);
        throw new Error(
          failure?.detail ||
            `Investigation request failed (${response.status})`,
        );
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();

      let buffer = "";
      let completed = false;

      const processMessage = (message: string) => {
        const dataLines = message
          .split(/\r?\n/)
          .filter((line) => line.startsWith("data:"))
          .map((line) => line.slice(5).trimStart());

        if (dataLines.length === 0) {
          return;
        }

        const payload: StreamPayload = JSON.parse(dataLines.join("\n"));

        if (payload.type === "progress") {
          setEvents((previous) => [...previous, payload.data]);
        }

        if (payload.type === "complete") {
          completed = true;
          setReport(payload.data);
          void fetchHistory();
        }

        if (payload.type === "error") {
          throw new Error(payload.data.message);
        }
      };

      while (true) {
        const { done, value } = await reader.read();

        if (done) {
          buffer += decoder.decode();
          break;
        }

        buffer += decoder.decode(value, {
          stream: true,
        });

        const messages = buffer.split(/\r?\n\r?\n/);

        buffer = messages.pop() ?? "";

        for (const message of messages) {
          processMessage(message);
        }
      }

      if (buffer.trim()) {
        processMessage(buffer);
      }

      if (!completed) {
        throw new Error("Investigation ended without a final report.");
      }
    } catch (err) {
      console.error("Investigation failed:", err);

      setError(err instanceof Error ? err.message : "Investigation failed.");
    } finally {
      setLoading(false);
    }
  };

  /* =====================================================
     LOAD SAVED REPORT
  ===================================================== */

  const loadInvestigation = async (id: number) => {
    if (loading) return;

    try {
      setError(null);

      const response = await fetch(`${API_URL}/api/investigations/${id}`);

      if (!response.ok) {
        throw new Error("Failed to load investigation");
      }

      const data: InvestigationReport = await response.json();

      setReport({ ...data, investigation_id: id });
      if (data.scenario_id) setSelectedScenario(data.scenario_id);
      if (data.mode) setMode(data.mode);
      setBugReport(data.bug_report);
      setEvents(data.events || (data.error ? [{ stage: "saved_error", status: "failed", message: `Saved failure: ${data.error}`, timestamp: data.timestamp }] : []));
      setView("workspace");
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to load investigation.",
      );
    }
  };

  /* =====================================================
     NAVIGATION
  ===================================================== */

  const navigate = (nextView: View) => {
    setView(nextView);
  };

  /* =====================================================
     UI
  ===================================================== */

  const activeScenario = scenarios.find((item) => item.id === selectedScenario);
  const testCount = (tests?: TestSummary | null) =>
    tests ? `${tests.passed} / ${tests.total}` : "Not run";

  // Keep the active evidence visible when the introduction collapses,
  // including on phones where setup and results are stacked.
  useEffect(() => {
    if (loading || report) {
      document.getElementById("evidence")?.scrollIntoView({ block: "start" });
    }
  }, [loading, report]);

  const loadRecorded = async () => {
    if (loading) return;
    try {
      const response = await fetch("/evidence/recorded-investigation.json");
      if (!response.ok)
        throw new Error("Recorded evidence could not be loaded.");
      const data: InvestigationReport = await response.json();
      setReport({ ...data, recorded_example: true });
      setView("workspace");
      setError(null);
      setEvents([]);
      if (data.mode) setMode(data.mode);
      if (data.scenario_id) setSelectedScenario(data.scenario_id);
      setBugReport(data.bug_report);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Could not load recording.",
      );
    }
  };

  const goToDesk = () => {
    document
      .getElementById("investigation")
      ?.scrollIntoView({ block: "start" });
    document.getElementById("scenario")?.focus({ preventScroll: true });
  };

  const loadShippingExample = () => {
    const example = scenarios.find((scenario) => scenario.id === "shipping");
    if (!example || loading) return;
    setSelectedScenario(example.id);
    setBugReport(example.default_bug_report);
    setMode("audit");
    setReport(null);
    setEvents([]);
    setError(null);
    goToDesk();
  };

  return (
    <div className="arena">
      <a
        className="skip-link"
        href={view === "workspace" ? "#investigation" : "#main"}
      >
        Skip to investigation
      </a>
      <header className="topbar">
        <Link href="/" className="brand" aria-label="AgentArena home">
          <svg
            className="brand-mark"
            viewBox="0 0 32 32"
            fill="none"
            aria-hidden="true"
          >
            <path
              d="M10 5H4v22h6M22 5h6v22h-6M19 9l-6 14"
              stroke="currentColor"
              strokeWidth="2.4"
            />
          </svg>
          <span>
            agentarena<span className="brand-period">.</span>
          </span>
        </Link>
        <nav aria-label="Main navigation">
          <button
            className={view === "workspace" ? "nav-item active" : "nav-item"}
            aria-current={view === "workspace" ? "page" : undefined}
            onClick={() => navigate("workspace")}
          >
            Workbench
          </button>
          <button
            className={view === "history" ? "nav-item active" : "nav-item"}
            aria-current={view === "history" ? "page" : undefined}
            onClick={() => navigate("history")}
          >
            Run history <span className="count">{history.length}</span>
          </button>
          <Link className="nav-item" href="/benchmarks">
            Evidence &amp; benchmark
          </Link>
        </nav>
        <div className="connection">
          <span className={`status-dot ${connectionState}`} />
          <span>
            {connectionState === "checking"
              ? "Connecting to API"
              : connectionState === "online"
                ? "API connected"
                : "API offline"}
          </span>
        </div>
      </header>

      <main id="main" className="workbench">
        {view === "workspace" && !report && !loading ? (
          <section className="review-intro" aria-labelledby="intro-title">
            <div className="intro-copy">
              <p className="eyebrow">
                <span className="ink-rule" /> CODE REVIEW, WITH RECEIPTS.
              </p>
              <h1 id="intro-title">
                A fix is a claim.
                <br />
                <span>Make it prove itself.</span>
              </h1>
              <p className="intro">
                Give a coding agent a bug. Examine its patch. Test the cases the
                original suite missed.
              </p>
              <div className="intro-action">
                <button className="desk-link" onClick={goToDesk}>
                  Run an investigation <ArrowDown size={17} />
                </button>
                <button
                  className="text-button"
                  onClick={() => void loadRecorded()}
                >
                  Inspect a recorded run <ArrowUpRight size={14} />
                </button>
              </div>
            </div>
            <aside
              className="specimen"
              aria-label="Illustrative shipping bug from the built-in scenarios"
            >
              <div className="specimen-heading">
                <span className="eyebrow">EXHIBIT 01 / SHIPPING.PY</span>
                <span className="specimen-index">[ ! ]</span>
              </div>
              <h2>
                The tests passed.
                <br />
                The bug stayed.
              </h2>
              <div className="specimen-code">
                <div>
                  <span>01</span>
                  <code>def calculate_shipping(weight):</code>
                </div>
                <div className="suspect-line">
                  <span>02</span>
                  <code> if weight &lt; 1:</code>
                  <span className="line-note">← the boundary</span>
                </div>
                <div>
                  <span>03</span>
                  <code> return 5</code>
                </div>
              </div>
              <dl className="specimen-results">
                <div>
                  <dt>Original test suite</dt>
                  <dd className="pass">
                    <Check size={13} />4 / 4 passed
                  </dd>
                </div>
                <div>
                  <dt>Package weighing exactly 1 kg</dt>
                  <dd className="fail">
                    $10 <span>≠ $5</span>
                  </dd>
                </div>
              </dl>
              <p className="specimen-note">
                An example from the built-in shipping scenario, not a live
                result.
              </p>
              <button
                className="specimen-link"
                disabled={
                  loading ||
                  !health ||
                  !scenarios.some((scenario) => scenario.id === "shipping")
                }
                onClick={loadShippingExample}
              >
                Investigate this case <ArrowRight size={15} />
              </button>
            </aside>
          </section>
        ) : (
          <div className="page-heading">
            <div>
              <p className="eyebrow">
                AGENTARENA /{" "}
                {view === "history" ? "RUN ARCHIVE" : "INVESTIGATION"}
              </p>
              <h1>
                {view === "history"
                  ? "The record of every run."
                  : loading
                    ? "Follow the investigation."
                    : "Read the evidence."}
              </h1>
              <p className="intro">
                {view === "history"
                  ? "Reopen a run to inspect its patch, findings, and verdict."
                  : loading
                    ? "The agent is working. The execution log records each stage."
                    : report?.bug_report}
              </p>
            </div>
            {view === "workspace" && !loading && (
              <button
                className="text-button"
                onClick={() => {
                  setReport(null);
                  setEvents([]);
                  setError(null);
                }}
              >
                Set up another run <ArrowUpRight size={15} />
              </button>
            )}
          </div>
        )}

        {connectionState === "offline" && (
          <div className="notice" role="status">
            <TriangleAlert size={17} />
            <div>
              <strong>Live investigations are currently unavailable</strong>
              <p>
                You can still inspect a recorded investigation and the published
                benchmark. Live runs need the connected Docker backend.
              </p>
            </div>
            <button
              className="text-button"
              onClick={() => setConnectionAttempt((n) => n + 1)}
            >
              <RotateCw size={14} /> Retry
            </button>
          </div>
        )}
        {report?.recorded_example && (
          <div className="notice" role="status">
            <strong>RECORDED INVESTIGATION</strong>
            <p>
              Saved on {formatDate(report.timestamp)}. This is supplied
              historical execution evidence, not a live run. New reference
              controls were not part of this recording.
            </p>
          </div>
        )}
        {error && (
          <div className="notice error" role="alert">
            <TriangleAlert size={17} />
            <span>{error}</span>
          </div>
        )}

        {view === "workspace" ? (
          <>
            <div className="desk-heading" id="investigation" tabIndex={-1}>
              <div>
                <span className="eyebrow">THE REVIEW DESK</span>
                <h2>From bug report to verdict.</h2>
              </div>
              <p>A patch. A challenge. A record of what happened.</p>
            </div>
            <div className={`workspace-grid ${isCustom ? "custom-workspace" : ""}`}>
              <aside className="setup-panel" aria-label="Investigation setup">
                <div className="section-heading">
                  <span className="section-number">01</span>
                  <h3>Describe the bug</h3>
                </div>
                <form
                  onSubmit={(event) => {
                    event.preventDefault();
                    void handleInvestigation();
                  }}
                >
                  <label htmlFor="scenario">Code to review</label>
                  <div className="select-wrap">
                    <GitBranch size={16} />
                    <select
                      id="scenario"
                      disabled={loading || !scenarios.length}
                      value={selectedScenario}
                      onChange={(event) => {
                        const id = event.target.value;
                        setSelectedScenario(id);
                        if (id === "custom") { setMode("audit"); setBugReport(""); }
                        const selected = scenarios.find(
                          (item) => item.id === id,
                        );
                        if (selected) setBugReport(selected.default_bug_report);
                      }}
                    >
                      <option value="custom">Your Python code</option>
                      {!scenarios.length && !isCustom && (
                        <option value={selectedScenario}>
                          {connectionState === "checking"
                            ? "Loading scenarios…"
                            : "Connect API to load scenarios"}
                        </option>
                      )}
                      {scenarios.map((scenario) => (
                        <option key={scenario.id} value={scenario.id}>
                          {scenario.name}
                        </option>
                      ))}
                    </select>
                  </div>
                  {isCustom && (
                    <div className="custom-inputs">
                      <p className="field-note">Paste one Python module. Audit only; standard library and pytest. No dependency installation.</p>
                      {connectionState !== "checking" && !health?.features?.custom_audit && <p className="field-note">Custom audits are not enabled on this backend.</p>}
                      <label htmlFor="custom-source">Your code · solution.py</label>
                      <textarea id="custom-source" className="custom-code" value={sourceCode} onChange={(event) => setSourceCode(event.target.value)} maxLength={20000} rows={12} spellCheck={false} disabled={loading} placeholder="Paste your Python functions or classes here" />
                      <p className="field-note">{sourceCode.length.toLocaleString()} / 20,000 characters</p>
                      <label htmlFor="custom-tests">Existing pytest tests (optional)</label>
                      <textarea id="custom-tests" className="custom-code" value={existingTests} onChange={(event) => setExistingTests(event.target.value)} maxLength={12000} rows={6} spellCheck={false} disabled={loading} placeholder={"from solution import your_function\n\ndef test_example():\n    assert your_function() == expected"} />
                      <p className="field-note">Without tests, the baseline checks only whether the module imports. Code and requirements are sent to Nebius. Results are not saved in shared history; download the report before leaving.</p>
                    </div>
                  )}
                  {!isCustom && activeScenario && (
                    <p className="field-note">{activeScenario.description}</p>
                  )}
                  <fieldset disabled={loading || isCustom}>
                    <legend>Investigation mode</legend>
                    <div className="mode-control">
                      {(["repair", "audit"] as const).map((value) => (
                        <button
                          type="button"
                          key={value}
                          aria-pressed={mode === value}
                          className={mode === value ? "selected" : ""}
                          onClick={() => setMode(value)}
                        >
                          {value === "repair"
                            ? "Repair + verify"
                            : "Audit only"}
                        </button>
                      ))}
                    </div>
                    <p className="field-note">
                      {mode === "repair"
                        ? "Ask the agent for a fix, then test it."
                        : "Test the existing code. Leave the source unchanged."}
                    </p>
                  </fieldset>
                  {!isCustom && <><label className="research-toggle">
                    <input
                      type="checkbox"
                      checked={enableResearch}
                      disabled={loading}
                      onChange={(event) =>
                        setEnableResearch(event.target.checked)
                      }
                    />{" "}
                    Use Tavily documentation research
                  </label>
                  <p className="field-note">
                    For the Safe Redirect Review, search is restricted to Python
                    3.11 documentation. Research can be disabled for comparison.
                  </p></>}
                  <div className="label-row">
                    <label htmlFor="bug-report">{isCustom ? "Expected behavior / bug report" : "Bug report"}</label>
                    <span>{bugReport.length}/3000</span>
                  </div>
                  <textarea
                    id="bug-report"
                    rows={7}
                    maxLength={3000}
                    disabled={loading}
                    value={bugReport}
                    onChange={(event) => setBugReport(event.target.value)}
                    placeholder="Describe the observed bug and expected behaviour."
                    required
                  />
                  <button
                    className="run-button"
                    type="submit"
                    disabled={
                      loading ||
                      !health || health.ready === false ||
                      !scenarios.length ||
                      !bugReport.trim() || (isCustom && (!sourceCode.trim() || !health?.features?.custom_audit))
                    }
                  >
                    {loading ? (
                      <Loader2 size={16} className="spin" />
                    ) : (
                      <Play size={15} fill="currentColor" />
                    )}
                    {loading
                      ? "Investigation running…"
                      : isCustom ? "Audit my code" : mode === "repair"
                        ? "Run investigation"
                        : "Run audit"}
                    {!loading && <ArrowUpRight size={17} />}
                  </button>
                  <p className="run-note">
                    {loading
                      ? "Keep this tab open while the run completes."
                      : "Inspect the diff, the test output, and the verdict."}
                  </p>
                </form>
                <div className="runtime">
                  <span className="eyebrow">RUNS ON</span>
                  <strong>NVIDIA Nemotron</strong>
                  <span>Nebius Token Factory</span>
                  <span className="runtime-detail">
                    {health
                      ? `Sandbox: ${health.sandbox}`
                      : "Runtime details appear after connection"}
                  </span>
                </div>
              </aside>

              <section
                id="evidence"
                className="evidence-panel"
                aria-label="Investigation evidence"
                aria-busy={loading}
              >
                <div className="section-heading">
                  <span className="section-number">02</span>
                  <h3>Read the evidence</h3>
                  <span className="run-id">
                    {report?.investigation_id
                      ? `RUN #${String(report.investigation_id).padStart(3, "0")}`
                      : report?.custom_audit ? "PRIVATE AUDIT" : loading
                        ? "RUN IN PROGRESS"
                        : "NO ACTIVE RUN"}
                  </span>
                </div>
                {report ? (
                  <>
                    {report.custom_audit && <div className="custom-notice" role="status">
                      <strong>CUSTOM CODE · NO REFERENCE CONTROL</strong>
                      <p>This report reproduces test outcomes against your specification. It does not certify correctness and is not stored in shared history.</p>
                      <button type="button" className="text-button" onClick={() => {
                        const url = URL.createObjectURL(new Blob([JSON.stringify(report, null, 2)], { type: "application/json" }));
                        const anchor = document.createElement("a"); anchor.href = url; anchor.download = "agentarena-custom-audit.json"; anchor.click();
                        setTimeout(() => URL.revokeObjectURL(url), 1000);
                      }}>Download report ↗</button>
                    </div>}
                    <div
                      className={`verdict ${statusClass(report.status)}`}
                      role="status"
                    >
                      <span className="verdict-icon">
                        {report.status === "PASSED_CHECKS" ? (
                          <Check size={21} />
                        ) : (
                          <TriangleAlert size={21} />
                        )}
                      </span>
                      <div>
                        <p className="eyebrow">WHAT THE CHECKS FOUND</p>
                        <h3>{report.custom_audit ? (report.assessment === "failures_reproduced" ? "Failures reproduced · needs review" : report.assessment === "checks_passed" ? "Checks passed · unvalidated" : "Inconclusive") : statusLabel(report.status)}</h3>
                        <p>
                          {report.explanation ||
                            "Review the test results and evidence below."}
                        </p>
                      </div>
                    </div>
                    {report.reference_validation && (
                      <div
                        className={`reference-control ${report.reference_validation.success ? "pass" : "pending"}`}
                      >
                        <strong>
                          Corrected reference control:{" "}
                          {report.reference_validation.success
                            ? "passed"
                            : "needs review"}
                        </strong>
                        <p>
                          The same generated suite ran against a curated
                          corrected implementation withheld from the agent.{" "}
                          {report.reference_validation.summary.passed}/
                          {report.reference_validation.summary.total} passed.
                        </p>
                      </div>
                    )}
                    {report.model && (
                      <p className="model-label">Model: {report.model}</p>
                    )}
                    <div className="metrics">
                      <div>
                        <span>Test pass score</span>
                        <strong>
                          {report.evidence_score ?? "—"}
                          <small>
                            {report.evidence_score != null ? "/100" : ""}
                          </small>
                        </strong>
                      </div>
                      <div>
                        <span>{report.original_tests_label || "Original tests"}</span>
                        <strong>{testCount(report.original_tests)}</strong>
                      </div>
                      <div>
                        <span>Adversarial tests</span>
                        <strong>{testCount(report.adversarial_tests)}</strong>
                      </div>
                    </div>
                    <div className="report-columns">
                      <section className="patch-section">
                        <div className="subheading">
                          <FileCode2 size={15} />
                          <h4>The patch</h4>
                        </div>
                        <DiffViewer diff={report.patch_diff || ""} />
                        {report.coding_summary && (
                          <details className="report-detail">
                            <summary>Agent summary</summary>
                            <p>{report.coding_summary}</p>
                          </details>
                        )}
                      </section>
                      <section className="findings-section">
                        <div className="subheading">
                          <FlaskConical size={15} />
                          <h4>The challenge</h4>
                        </div>
                        {report.failures?.length ? (
                          report.failures.map((failure, index) => (
                            <article
                              className="finding"
                              key={`${failure.test_name}-${index}`}
                            >
                              <span className="failure-label">
                                {failure.category}
                              </span>
                              <h5>{failure.test_name}</h5>
                              <p>{failure.explanation}</p>
                              <details open>
                                <summary>Failure evidence</summary>
                                <pre>{failure.evidence}</pre>
                              </details>
                            </article>
                          ))
                        ) : (
                          <div className="no-findings">
                            <Circle size={17} />
                            <p>
                              {report.status === "PASSED_CHECKS"
                                ? "The checks run did not report a failure."
                                : "No detailed failures were returned. Review the verdict and verifier analysis."}
                            </p>
                            <span>
                              These checks do not prove the absence of other
                              defects.
                            </span>
                          </div>
                        )}
                        {report.verifier_analysis && (
                          <details className="report-detail">
                            <summary>Verifier analysis</summary>
                            <p>{report.verifier_analysis}</p>
                          </details>
                        )}
                      </section>
                    </div>

                    {!!report.test_evidence?.length && (
                      <section className="provenance-section">
                        <div className="subheading">
                          <FileCode2 size={15} />
                          <h4>Source → test → execution</h4>
                        </div>
                        <p>
                          {report.custom_audit
                            ? "Tests are checked against your supplied specification and code. No corrected reference is available; review each expectation."
                            : "Excerpt matching verifies provenance, not that a source proves the assertion correct. The reference control tests the expected behaviour separately."}
                        </p>
                        {report.test_evidence.map((test) => (
                          <article
                            className="provenance-test"
                            key={test.test_name}
                          >
                            <strong>{test.test_name}</strong>
                            <p>{test.rationale}</p>
                            <p>
                              <b>Expected:</b>{" "}
                              {test.expected_behavior || "See generated test"}
                            </p>
                            {test.specification_refs?.map((ref, index) => (
                              <div key={`spec-${index}`}>
                                <small>Supplied specification · excerpt matched</small>
                                <blockquote>{ref.quote}</blockquote>
                              </div>
                            ))}
                            {!!test.citation_checks?.length && (
                              <details>
                                <summary>Citation checks ({test.citation_checks.length})</summary>
                                {test.citation_checks.map((check, index) => (
                                  <div key={index}>
                                    <p>{check.source_id || "Missing source ID"}: {check.status} — {check.reason.replaceAll("_", " ")}</p>
                                    {check.claimed_quote && <blockquote>{check.claimed_quote}</blockquote>}
                                  </div>
                                ))}
                              </details>
                            )}
                            {test.sources.length ? (
                              test.sources.map((ref, index) => (
                                <div key={index}>
                                  <a
                                    href={ref.url}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                  >
                                    {ref.source_id}: {ref.title || ref.url} ↗
                                  </a>
                                  <blockquote>{ref.quote}</blockquote>
                                  <small>{ref.verification}</small>
                                </div>
                              ))
                            ) : (
                              <small>
                                No verified source excerpt. This test relies on
                                the supplied specification and code.
                              </small>
                            )}
                          </article>
                        ))}
                      </section>
                    )}
                    {!!report.agent_trace?.length && (
                      <details className="generated-tests">
                        <summary>
                          Inspect the coding agent’s observed actions
                        </summary>
                        <pre>{JSON.stringify(report.agent_trace, null, 2)}</pre>
                      </details>
                    )}
                    {report.generated_test_source && (
                      <details className="generated-tests">
                        <summary>
                          Inspect the complete generated test suite
                        </summary>
                        <pre>{report.generated_test_source}</pre>
                      </details>
                    )}
                    {report.research && report.research.enabled && (
                      <section
                        className="research-section"
                        aria-labelledby="research-heading"
                      >
                        <div className="research-heading">
                          <div className="subheading">
                            <BookOpen size={15} />
                            <h4 id="research-heading">Research evidence</h4>
                          </div>

                          <span
                            className={`research-status ${
                              report.research.status === "completed"
                                ? "pass"
                                : "pending"
                            }`}
                          >
                            {report.research.status}
                          </span>
                        </div>

                        <div className="research-meta">
                          <div>
                            <span>RESEARCH PROVIDER</span>
                            <strong>Tavily</strong>
                          </div>

                          <div>
                            <span>SOURCES CONSULTED</span>
                            <strong>
                              {report.research.sources?.length ?? 0}
                            </strong>
                          </div>

                          <div>
                            <span>CACHE</span>
                            <strong>
                              {report.research.cached ? "HIT" : "MISS"}
                            </strong>
                          </div>
                        </div>

                        {report.research.query && (
                          <div className="research-query">
                            <span className="research-label">SEARCH QUERY</span>
                            <p>{report.research.query}</p>
                          </div>
                        )}

                        {!!report.research.insights?.length && (
                          <div className="research-insights">
                            <span className="research-label">
                              RESEARCH INSIGHTS
                            </span>

                            <ol>
                              {report.research.insights.map(
                                (insight, index) => (
                                  <li key={index}>{insight}</li>
                                ),
                              )}
                            </ol>
                          </div>
                        )}

                        {!!report.research.sources?.length && (
                          <div className="research-sources">
                            <span className="research-label">REFERENCES</span>

                            <div className="research-source-list">
                              {report.research.sources.map((source, index) => {
                                let safeUrl: string | null = null;

                                try {
                                  const parsed = new URL(source.url);
                                  if (
                                    parsed.protocol === "https:" ||
                                    parsed.protocol === "http:"
                                  ) {
                                    safeUrl = parsed.href;
                                  }
                                } catch {
                                  safeUrl = null;
                                }

                                if (!safeUrl) return null;

                                return (
                                  <a
                                    href={safeUrl}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="research-source"
                                    key={`${source.url}-${index}`}
                                  >
                                    <span className="research-source-index">
                                      {String(index + 1).padStart(2, "0")}
                                    </span>

                                    <span className="research-source-info">
                                      <strong>
                                        {source.title || "Untitled reference"}
                                      </strong>

                                      <small>{new URL(safeUrl).hostname}</small>
                                    </span>

                                    <ArrowUpRight size={15} />
                                  </a>
                                );
                              })}
                            </div>
                          </div>
                        )}

                        {report.research.error && (
                          <p className="research-error">
                            Research service: {report.research.error}
                          </p>
                        )}

                        <p className="research-disclaimer">
                          External references inform test generation. They do
                          not establish repository requirements or independently
                          prove a defect. Verification is based on executed
                          tests and available specifications.
                        </p>
                      </section>
                    )}
                  </>
                ) : (
                  <div
                    className={`empty-evidence ${loading ? "is-running" : ""}`}
                  >
                    <div className="empty-symbol">
                      {loading ? (
                        <Loader2 size={30} className="spin" />
                      ) : (
                        <FileCode2 size={30} strokeWidth={1.3} />
                      )}
                    </div>
                    <p className="eyebrow">
                      {loading
                        ? "INVESTIGATION IN PROGRESS"
                        : "AWAITING YOUR FIRST RUN"}
                    </p>
                    <h3>
                      {loading
                        ? "Checking the claim."
                        : "No verdict without evidence."}
                    </h3>
                    <p>
                      {loading
                        ? "Follow the execution log below. The patch and verification results will appear here when the run finishes."
                        : "Start a run on the left. This space will hold the patch, the tests that challenge it, and the final verdict."}
                    </p>
                    <div className="evidence-steps">
                      <span>
                        <span>01</span> Patch
                      </span>
                      <ChevronRight size={14} />
                      <span>
                        <span>02</span> Challenge
                      </span>
                      <ChevronRight size={14} />
                      <span>
                        <span>03</span> Verdict
                      </span>
                    </div>
                  </div>
                )}
                {report?.error && (
                  <details className="execution-log">
                    <summary>Saved failure diagnostics</summary>
                    <pre>{report.error}</pre>
                  </details>
                )}
                <details className="execution-log" open={loading || undefined}>
                  <summary>
                    <Terminal size={15} />
                    <span>Execution log</span>
                    <span className="log-count">
                      {events.length
                        ? `${events.length} events`
                        : report ? "No saved events" : "Awaiting run"}
                    </span>
                    {loading && <span className="status-dot online" />}
                  </summary>
                  <div className="log-body" role="log" aria-live="polite">
                    {events.length ? (
                      events.map((event, index) => (
                        <div className="log-entry" key={index}>
                          <time>
                            {new Date(event.timestamp).toLocaleTimeString()}
                          </time>
                          <span
                            className={`event-status ${event.status === "completed" ? "pass" : ["failed", "error"].includes(event.status) ? "fail" : "pending"}`}
                          >
                            {event.status}
                          </span>
                          <span>{event.message}</span>
                        </div>
                      ))
                    ) : (
                      <p>
                        {report ? "This older report has no saved execution events. Its verdict and any saved error are retained." : "Commands and progress events will appear when an investigation starts."}
                      </p>
                    )}
                  </div>
                </details>
              </section>
            </div>
          </>
        ) : (
          <section className="history-panel" aria-label="Saved investigations">
            <div className="section-heading">
              <h2>Saved investigations</h2>
              <button
                className="text-button"
                disabled={loading}
                onClick={() => void fetchHistory()}
              >
                <RotateCw size={14} /> Refresh
              </button>
            </div>
            {historyError && (
              <p className="history-error" role="alert">
                {historyError}
              </p>
            )}
            {history.length ? (
              <div className="history-list">
                {history.map((item) => (
                  <button
                    className="history-row"
                    disabled={loading}
                    key={item.id}
                    onClick={() => void loadInvestigation(item.id)}
                  >
                    <span className="history-id">
                      #{String(item.id).padStart(3, "0")}
                    </span>
                    <span className="history-description">
                      <strong>{item.bug_report}</strong>
                      <time>{formatDate(item.created_at)}</time>
                    </span>
                    <span
                      className={`result-label ${statusClass(item.status)}`}
                    >
                      {statusLabel(item.status)}
                    </span>
                    <span className="history-score">
                      {item.evidence_score ?? "—"}
                      <small>/100</small>
                    </span>
                    <ChevronRight size={16} />
                  </button>
                ))}
              </div>
            ) : (
              <div className="history-empty">
                <Terminal size={25} />
                <h3>No saved investigations yet</h3>
                <p>Completed runs appear here when the API is connected.</p>
                <button
                  className="text-button"
                  onClick={() => navigate("workspace")}
                >
                  Go to workspace <ArrowUpRight size={15} />
                </button>
              </div>
            )}
          </section>
        )}
        <footer className="footer">
          <div>
            <strong>agentarena.</strong>
            <span>Less guesswork. More evidence.</span>
          </div>
          <span>
            NVIDIA Nemotron <span className="footer-slash">/</span> Nebius Token
            Factory
          </span>
        </footer>
      </main>
    </div>
  );
}
