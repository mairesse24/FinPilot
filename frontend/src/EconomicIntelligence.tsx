import { useEffect, useRef, useState } from "react";
import "./connected.css";
import ScoreRing from "./ScoreRing";
import { useFinancialWorkspace } from "./FinancialWorkspace";
import { DeliveryStatus, type Delivery } from "./FloatingCopilot";
import ReliabilityNotices from "./ReliabilityNotices";
import { API_BASE, type Notice } from "./api";
import ChatRichText from "./ChatRichText";
import { useFinance, useHealthScore } from "./financeStore";
import { SpendingCutSimulator, factorHelp, isDebug } from "./dashboardParts";

type Facts = Record<string, string | boolean>;
type Component = {
  name: string;
  score: number | null;
  weight: number;
  formula: string;
  reason: string;
};
type Health = {
  version: string;
  score: number | null;
  observed_score: number;
  observed_score_basis: string;
  observed_score_explanation: string;
  observed_score_confidence: "low" | "medium" | "high";
  observed_score_limitations: string[];
  components: Component[];
  metrics: Record<string, number | string | null>;
  warnings: string[];
  withheld_reasons: string[];
  completeness: { available_components: number; required_components: number };
};
type Economy = {
  as_of: string;
  status: string;
  labels: string[];
  pressure_breadth_index: number | null;
  method: string;
  dimensions: { name: string; available: boolean; signals: string[]; explanation: string }[];
  indicators: {
    id: string;
    value: number;
    observation_date: string;
    knowledge_date: string;
    initial_release_date?: string | null;
    retrieved_at: string;
    age_days: number;
    stale: boolean;
    units: string;
    frequency: string;
    publisher: string;
    source_url: string;
  }[];
  features: Record<string, number | null>;
  provider_errors: Record<string, string>;
};
type Scenario = { type: string; fraction?: number; amount?: number; delay_days?: number };
type Exposure = { id: string; cause: string; action: string; scenario: Scenario };
type Context = {
  data_notices?: Notice[];
  baseline_health: Health;
  economic_conditions: Economy;
  alerts: Exposure[];
  financial_alerts?: { id: string; cause: string; action: string }[];
  note: string;
};
type Cash = {
  status: string;
  minimum_checking: number;
  ending_checking: number;
  series: { date: string; balance: number }[];
  alerts: { cause: string }[];
  note: string;
};
type Simulation = {
  before: { health: Health; cash_plan: Cash };
  after: { health: Health; cash_plan: Cash; guardian_alerts: { id: string; cause: string }[] };
  score_changes: {
    component: string;
    before: number | null;
    after: number | null;
    difference: number | null;
    explanation: string;
  }[];
  ending_checking_change: number;
  net_worth_change: number;
  note: string;
};
const scenarioLabels: Record<string, string> = {
  essential_cost_increase: "Essential costs rise",
  cash_expense_increase: "Everyday cash spending rises",
  income_reduction: "Income drops",
  income_interruption: "Income stops for a while",
  missed_paycheck: "A paycheck is missed",
  emergency_expense: "Unexpected expense",
  variable_rate_payment: "Variable-rate payment rises",
  delayed_paycheck: "A paycheck arrives late",
  fixed_bill_increase: "A fixed bill increases",
  savings_transfer: "Move money to savings",
};
const humanize = (id: string) => {
  const t = id.replace(/_/g, " ");
  return t.charAt(0).toUpperCase() + t.slice(1);
};
const loadErrorText = (reason: unknown) => {
  const m = reason instanceof Error ? reason.message : String(reason);
  return /not found|404/i.test(m) && !isDebug() ? "Some FinPilot data could not be loaded yet. Please try again in a moment." : m;
};
const currency = (n: number) => n.toLocaleString("en-US", { style: "currency", currency: "USD" });
async function request<T>(path: string, body?: object, signal?: AbortSignal): Promise<T> {
  const response = await fetch(API_BASE + "/api/" + path, {
    signal,
    cache: "no-store",
    method: body ? "POST" : "GET",
    headers: body ? { "Content-Type": "application/json" } : undefined,
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!response.ok) {
    const detail = await response.json().catch(() => ({}));
    const fields: Record<string, string> = { ...(detail.field_errors ?? {}) };
    if (Array.isArray(detail.detail))
      for (const item of detail.detail) fields[item.loc?.slice(2).join(".") || "input"] = item.msg;
    throw new InputError(
      typeof detail.detail === "string"
        ? detail.detail
        : Object.entries(fields)
            .map(([k, v]) => `${k.replace(/_/g, " ")}: ${v}`)
            .join("; ") || `Request failed (${response.status}).`,
      fields,
    );
  }
  return response.json() as Promise<T>;
}

type Constraints = {
  savings_balance: number;
  essential_bill_floor: number;
  discretionary_bill_floor: number;
  known_required_debt: number;
  dated_debt_payments: number;
  scheduled_income: number;
  bills: { name: string; amount: number; category: string; frequency: string; due_date: string }[];
};
class InputError extends Error {
  constructor(
    message: string,
    public fields: Record<string, string> = {},
  ) {
    super(message);
  }
}
function ErrorSummary({ message }: { message: string }) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    ref.current?.focus();
  }, [message]);
  return (
    <div className="form-error" role="alert" tabIndex={-1} ref={ref}>
      <strong>Check your inputs</strong>
      <p>{message}</p>
    </div>
  );
}
function dimensionTone(d: { available: boolean; signals: string[] } | undefined) {
  return !d?.available
    ? "unknown"
    : d.signals.length >= 3
      ? "red"
      : d.signals.length === 2
        ? "orange"
        : d.signals.length === 1
          ? "yellow"
          : "green";
}

function CashChart({ result }: { result: Simulation }) {
  const a = result.before.cash_plan.series,
    b = result.after.cash_plan.series;
  const all = [...a, ...b].map((r) => r.balance),
    lo = Math.min(...all),
    hi = Math.max(...all),
    span = Math.max(1, hi - lo);
  const points = (rows: typeof a) =>
    rows
      .map(
        (r, i) =>
          `${20 + (i * 760) / Math.max(1, rows.length - 1)},${210 - ((r.balance - lo) / span) * 180}`,
      )
      .join(" ");
  return (
    <figure>
      <svg
        viewBox="0 0 800 240"
        role="img"
        aria-label="Baseline and hypothetical checking cash plans"
      >
        <polyline points={points(a)} fill="none" stroke="#94a3b8" strokeWidth="3" />
        <polyline points={points(b)} fill="none" stroke="#00e5c3" strokeWidth="3" />
      </svg>
      <figcaption>
        Gray: baseline budget plan. Teal: hypothetical plan. Range {currency(lo)} to {currency(hi)}.
        These are deterministic assumptions, not ML predictions.
      </figcaption>
    </figure>
  );
}

export default function EconomicIntelligence({ page }: { page: string }) {
  const { facts, setFacts, confirmedFacts, setConfirmedFacts } = useFinancialWorkspace();
  const { health: v1 } = useHealthScore();
  const fin = useFinance(30);
  const [attempt, setAttempt] = useState(0);
  const inputs = useRef<HTMLFormElement>(null);
  const [inputsOpen, setInputsOpen] = useState(false);
  const [delivery, setDelivery] = useState<Delivery | null>(null);
  const [context, setContext] = useState<Context | null>(null);
  const [error, setError] = useState("");
  const [errorScope, setErrorScope] = useState("loading");
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [constraints, setConstraints] = useState<Constraints | null>(null);
  const [dirty, setDirty] = useState(false);
  const [assessmentDone, setAssessmentDone] = useState(false);
  const healthSummary = useRef<HTMLElement>(null);
  const [busy, setBusy] = useState(false);
  const [scenario, setScenario] = useState<Scenario>({
    type: "essential_cost_increase",
    fraction: 0.1,
    amount: 1000,
    delay_days: 7,
  });
  const [simulation, setSimulation] = useState<Simulation | null>(null);
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState("");
  const payload = () =>
    Object.fromEntries(
      Object.entries(facts)
        .filter(([, v]) => v !== "")
        .map(([k, v]) => [k, typeof v === "boolean" ? v : Number(v)]),
    );
  useEffect(() => {
    const controller = new AbortController();
    setError("");
    // One missing endpoint must not blank the whole page: the profile is required, the input limits are optional.
    Promise.allSettled([
      request<Context>("resilience", { facts: confirmedFacts ?? {} }, controller.signal),
      request<Constraints>("financial-inputs", undefined, controller.signal),
    ]).then(([c, limits]) => {
      if (controller.signal.aborted) return;
      if (c.status === "fulfilled") setContext(c.value);
      else {
        // The load error must show even after the user has run an assessment, simulation or chat.
        setErrorScope("loading");
        setError(loadErrorText(c.reason));
      }
      if (limits.status === "fulfilled") setConstraints(limits.value);
    });
    return () => controller.abort();
  }, [attempt]);
  const updateFact = (key: string, value: string | boolean) => {
    setFacts((f) => ({ ...f, [key]: value }));
    setDirty(true);
    setConfirmedFacts(null);
    setAssessmentDone(false);
    setSimulation(null);
    setAnswer("");
    setError("");
    setFieldErrors({});
  };
  const validate = () => {
    const errors: Record<string, string> = {};
    for (const [key, value] of Object.entries(facts))
      if (
        typeof value === "string" &&
        value !== "" &&
        (!Number.isFinite(Number(value)) || Number(value) < 0)
      )
        errors[key] = "Enter a finite amount of zero or more.";
    if (
      constraints &&
      facts.accessible_emergency_savings !== undefined &&
      facts.accessible_emergency_savings !== "" &&
      Number(facts.accessible_emergency_savings) > Math.max(0, constraints.savings_balance)
    )
      errors.accessible_emergency_savings = `Accessible emergency savings cannot exceed your imported savings total of ${currency(Math.max(0, constraints.savings_balance))}. Enter the accessible portion of these accounts, or import missing accounts first.`;
    if (constraints && facts.bills_complete) {
      if (
        facts.essential_cash_expenses !== undefined &&
        facts.essential_cash_expenses !== "" &&
        Number(facts.essential_cash_expenses) < constraints.essential_bill_floor
      )
        errors.essential_cash_expenses = `Include at least ${currency(constraints.essential_bill_floor)} in known monthly essential bills.`;
      if (
        facts.discretionary_cash_expenses !== undefined &&
        facts.discretionary_cash_expenses !== "" &&
        Number(facts.discretionary_cash_expenses) < constraints.discretionary_bill_floor
      )
        errors.discretionary_cash_expenses = `Include at least ${currency(constraints.discretionary_bill_floor)} in known monthly discretionary bills.`;
    }
    if (Object.keys(errors).length) throw new InputError(Object.values(errors).join(" "), errors);
  };
  const captureError = (e: unknown) => {
    setError((e as Error).message);
    setFieldErrors(e instanceof InputError ? e.fields : {});
  };
  const assess = async () => {
    setErrorScope("assessment");
    setAssessmentDone(false);
    setBusy(true);
    setError("");
    setSimulation(null);
    try {
      validate();
      setContext(await request<Context>("resilience", { facts: payload() }));
      setDirty(false);
      setFieldErrors({});
      setAssessmentDone(true);
      setConfirmedFacts(payload());
    } catch (e) {
      captureError(e);
    } finally {
      setBusy(false);
    }
  };
  const simulate = async (chosen = scenario) => {
    setErrorScope("simulation");
    setBusy(true);
    setSimulation(null);
    setError("");
    try {
      validate();
      const confirmed = payload();
      const [result, updated] = await Promise.all([
        request<Simulation>("economic-simulate", { facts: confirmed, scenario: chosen }),
        request<Context>("resilience", { facts: confirmed }),
      ]);
      setSimulation(result);
      setContext(updated);
      setConfirmedFacts(confirmed);
      setDirty(false);
      setFieldErrors({});
    } catch (e) {
      captureError(e);
    } finally {
      setBusy(false);
    }
  };
  const chat = async () => {
    if (!question.trim()) return;
    setErrorScope("chat");
    setBusy(true);
    setError("");
    try {
      const r = await request<{ reply: string; delivery?: Delivery }>("chat", {
        financial_facts: payload(),
        messages: [{ role: "user", content: question }],
      });
      setAnswer(r.reply);
      setDelivery(r.delivery ?? null);
    } catch (e) {
      captureError(e);
    } finally {
      setBusy(false);
    }
  };
  const economy = context?.economic_conditions,
    health = context?.baseline_health;
  const displayedScore = health
    ? dirty
      ? health.observed_score
      : (health.score ?? health.observed_score)
    : null;
  const scoreIsObserved = Boolean(health && (dirty || health.score == null));
  const headlineScore = scoreIsObserved && !dirty && v1 ? v1.score : displayedScore;
  const cutDefaults = fin.dashboard?.active_alerts.find((a) => a.suggested_scenario)?.suggested_scenario ?? null;
  const cutPanel = <SpendingCutSimulator defaults={cutDefaults} buffer={fin.forecast?.safety_buffer ?? null} />;
  const noEconomyData =
    !!economy && !economy.indicators.length && Object.values(economy.features).every((v) => v == null);
  const economyPanel = economy && (noEconomyData ? (
    <section className="live-panel">
      <h2>Economic conditions · {economy.as_of}</h2>
      <strong className="live-value">{economy.status}</strong>
      <div className="empty-state">
        <h3>Economic indicators are not available right now</h3>
        <p>
          FinPilot has not loaded its latest inflation, jobs and interest-rate data yet. Your personal
          forecast, score and Guardian alerts do not depend on it.
        </p>
        <small>Economic data is supplied as a dated snapshot and refreshed separately.</small>
      </div>
    </section>
  ) : (
    <section className="live-panel">
      <h2>Economic conditions · {economy.as_of}</h2>
      <strong className="live-value">{economy.status}</strong>
      <p>{economy.method}</p>
      <p>
        Pressure breadth: {economy.pressure_breadth_index ?? "Unavailable"} / 100. This is signal
        breadth, not a probability or a personal score.
      </p>
      <div className="live-grid">
        {[
          ["Headline CPI YoY (%)", economy.features.CPIAUCSL_yoy_pct],
          ["Core CPI YoY (%)", economy.features.CPILFESL_yoy_pct],
          ["PCE YoY (%)", economy.features.PCEPI_yoy_pct],
          [
            "Unemployment (%)",
            economy.indicators.find((i) => i.id === "UNRATE" && !i.stale)?.value,
          ],
          ["Federal funds (%)", economy.features.policy_rate_pct],
          ["10y minus 2y (pp)", economy.features.yield_spread_pp],
          ["Realized volatility (%)", economy.features.realized_vol20_annualized_pct],
          ["High-yield spread (%)", economy.features.credit_spread_pct],
        ].map(([label, value], i) => (
          <article
            className={`live-panel indicator-card tone-${typeof value !== "number" ? "unknown" : dimensionTone(economy.dimensions.find((d) => d.name === (i < 3 ? "inflation" : i === 3 ? "labor" : i === 6 ? "market" : "monetary_credit")))}`}
            key={String(label)}
          >
            <p>{label}</p>
            <strong className="live-value">
              {typeof value === "number" ? value.toFixed(2) : "Unavailable"}
            </strong>
          </article>
        ))}
      </div>
      <p className="color-legend">
        Descriptive signals: <span className="tone-green">none</span> /{" "}
        <span className="tone-yellow">one</span> / <span className="tone-orange">two</span> /{" "}
        <span className="tone-red">three or more</span> / gray: insufficient data. Colors are not
        market forecasts.
      </p>
      <div className="live-grid">
        {economy.dimensions.map((d) => (
          <article className={`live-panel indicator-card tone-${dimensionTone(d)}`} key={d.name}>
            <h3>{d.name.replace("_", " ")}</h3>
            <p>
              {!d.available
                ? "Insufficient data"
                : d.signals.join("; ") || "No configured pressure signal"}
            </p>
            <small>{d.explanation}</small>
          </article>
        ))}
      </div>
      <details>
        <summary>Indicator values, freshness and sources</summary>
        <div className="live-table">
          <table>
            <thead>
              <tr>
                <th>Series</th>
                <th>Value / units</th>
                <th>Observation</th>
                <th>Knowledge date</th>
                <th>Initial release date</th>
                <th>Frequency / freshness</th>
              </tr>
            </thead>
            <tbody>
              {economy.indicators.map((i) => (
                <tr key={i.id}>
                  <td>
                    <a href={i.source_url} target="_blank" rel="noreferrer">
                      {i.id}
                    </a>
                    <small>{i.publisher}</small>
                  </td>
                  <td>
                    {i.value.toFixed(3)} · {i.units}
                  </td>
                  <td>{i.observation_date}</td>
                  <td>{i.knowledge_date}</td>
                  <td>{i.initial_release_date ?? "Unknown"}</td>
                  <td>
                    {i.frequency} · {i.age_days} days old {i.stale ? "· STALE / excluded" : ""}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {isDebug() && Object.entries(economy.provider_errors).map(([k, v]) => (
          <p key={k}>
            {k}: {v}
          </p>
        ))}
        <p>
          Knowledge date is not an exact release timestamp. Historical adjusted Yahoo prices are
          excluded from point-in-time backtests.
        </p>
      </details>
    </section>
  ));
  const inputPanel = (
    <details
      className="live-panel optional-inputs"
      open={inputsOpen}
      onToggle={(e) => setInputsOpen(e.currentTarget.open)}
    >
      <summary>Review or correct imported assumptions <small>Optional</small></summary>
    <form
      ref={inputs}
      className="optional-input-form"
      noValidate
      onSubmit={(e) => {
        e.preventDefault();
        void assess();
      }}
    >
      <fieldset disabled={busy || !context} className="financial-fields">
        <h2>Refine your automatic score <small>Optional</small></h2>
        <p>
          Your score is already calculated from imported records. Add or correct these values when
          the bank snapshot cannot distinguish take-home income, cash budgets, or complete payment
          schedules. Essential/discretionary amounts include scheduled non-debt bills but exclude
          debt payments and savings transfers.
        </p>
        <div className="live-grid">
          {[
            ["take_home_income", "Monthly take-home income"],
            ["essential_cash_expenses", "Monthly essential cash expenses"],
            ["discretionary_cash_expenses", "Monthly discretionary cash expenses"],
            ["required_debt_payments", "Monthly required debt payments"],
            ["accessible_emergency_savings", "Accessible emergency savings"],
            ["variable_rate_balance", "Confirmed variable-rate debt (optional)"],
          ].map(([key, label]) => (
            <label key={key}>
              {label}
              <input
                aria-label={label}
                type="number"
                min="0"
                step="0.01"
                value={String(facts[key] ?? "")}
                aria-invalid={Boolean(fieldErrors[key])}
                aria-describedby={fieldErrors[key] ? `error-${key}` : undefined}
                onChange={(e) => updateFact(key, e.target.value)}
                style={{
                  display: "block",
                  width: "100%",
                  padding: 10,
                  background: "#162032",
                  border: "1px solid #334155",
                  color: "white",
                  borderRadius: 8,
                }}
              />
              {fieldErrors[key] && (
                <small className="field-error" id={`error-${key}`}>
                  {fieldErrors[key]}
                </small>
              )}
              {key === "accessible_emergency_savings" && constraints && (
                <small className="input-hint">
                  Imported savings: {currency(constraints.savings_balance)}. Include only available,
                  uncommitted savings.
                </small>
              )}
              {key === "essential_cash_expenses" && constraints && (
                <small className="input-hint">
                  Known monthly essential bills: {currency(constraints.essential_bill_floor)}.
                </small>
              )}
              {key === "required_debt_payments" && constraints && (
                <small className="input-hint">
                  Dated monthly debt payments: {currency(constraints.dated_debt_payments)}. Higher
                  obligations need their missing payment dates before a complete score can be
                  calculated.
                </small>
              )}
              {key === "required_debt_payments" &&
                constraints &&
                facts.debt_complete &&
                Number(facts.required_debt_payments) > constraints.dated_debt_payments && (
                  <small className="field-warning">
                    {currency(
                      Number(facts.required_debt_payments) - constraints.dated_debt_payments,
                    )}{" "}
                    of your declared monthly debt payments has no imported payment dates. A complete
                    score remains withheld until those dates are supplied.
                  </small>
                )}
            </label>
          ))}
        </div>
        <p>
          <label>
            <input
              type="checkbox"
              checked={Boolean(facts.bills_complete)}
              onChange={(e) => updateFact("bills_complete", e.target.checked)}
            />{" "}
            I confirm upcoming bills are complete for this assessment.
          </label>
        </p>
        <p>
          <label>
            <input
              type="checkbox"
              checked={Boolean(facts.debt_complete)}
              onChange={(e) => updateFact("debt_complete", e.target.checked)}
            />{" "}
            I confirm debt-payment information is complete, including confirmed zero debt if
            applicable.
          </label>
        </p>
        {error && errorScope === "assessment" && <ErrorSummary message={error} />}
        <button type="submit" disabled={busy || !context}>
          {busy && errorScope === "assessment" ? "Calculating..." : "Calculate assessment"}
        </button>
        {assessmentDone && !dirty && (
          <p role="status" className="assessment-status">
            Assessment updated.{" "}
            {context?.baseline_health.score == null
              ? "Some required information is still missing; review the unavailable components."
              : `Your score is ${context.baseline_health.score.toFixed(2)} out of 100.`}{" "}
            <button
              type="button"
              onClick={() => {
                healthSummary.current?.focus();
                healthSummary.current?.scrollIntoView({ block: "start", behavior: "smooth" });
              }}
            >
              View assessment
            </button>
          </p>
        )}
        <p>
          <label>
            <input
              type="checkbox"
              checked={Boolean(facts.income_history_complete)}
              onChange={(e) => updateFact("income_history_complete", e.target.checked)}
            />{" "}
            Classified income history covers complete months; calculate variability only if six
            months are available.
          </label>
        </p>
        <details>
          <summary>Payment calendar used by simulations</summary>
          <p>
            Assessment budgets do not change your imported payment dates. Add missing obligations
            through your banking data import to make the calendar complete.
          </p>
          {constraints && (
            <>
              <p>
                Scheduled income, normalized to 30 days: {currency(constraints.scheduled_income)}.
              </p>
              <div className="live-table">
                <table>
                  <thead>
                    <tr>
                      <th>Obligation</th>
                      <th>Amount</th>
                      <th>Frequency</th>
                      <th>Due date</th>
                    </tr>
                  </thead>
                  <tbody>
                    {constraints.bills.map((b, i) => (
                      <tr key={i}>
                        <td>{b.name}</td>
                        <td>{currency(b.amount)}</td>
                        <td>{b.frequency}</td>
                        <td>{b.due_date}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          )}
        </details>
      </fieldset>
    </form>
    </details>
  );
  const healthPanel = health && (
    <section
      className="live-panel"
      ref={healthSummary}
      tabIndex={-1}
      style={{ scrollMarginTop: 90 }}
    >
      <h2>Your financial health</h2>
      <ScoreRing score={headlineScore} estimated={scoreIsObserved} />
      {scoreIsObserved && (
        <div className="score-next-step">
          <p>
            <strong>Automatic estimate:</strong> calculated from imported accounts, transactions,
            bills and scheduled income. Current economic conditions inform resilience alerts and
            stress tests; they do not arbitrarily change this personal score.
          </p>
          <p><strong>Confidence: {health.observed_score_confidence}.</strong> {health.observed_score_explanation}</p>
          {health.observed_score_limitations.map((limit) => <p key={limit}>{limit}</p>)}
          <button
            onClick={() => {
              setInputsOpen(true);
              window.setTimeout(() => {
                inputs.current?.scrollIntoView({ block: "start", behavior: "smooth" });
                inputs.current?.querySelector<HTMLInputElement>('input[type="number"]')
                  ?.focus({ preventScroll: true });
              }, 0);
            }}
          >
            Improve estimate accuracy
          </button>
        </div>
      )}
      {!dirty && (
        <p>
          {scoreIsObserved && v1
            ? "This score combines every factor FinPilot can measure from your imported accounts, bills and spending. Confirm your inputs below for a more precise assessment."
            : health.score == null
              ? `Confirmed-input assessment: ${health.completeness.available_components} / ${health.completeness.required_components} components supported.`
              : "All confirmed-input components supported."}{" "}
          It is not a CFPB or credit score.
        </p>
      )}
      {!dirty && scoreIsObserved && v1 && (
        <details open>
          <summary>Score breakdown</summary>
          {v1.components.map((c) => (
            <article key={c.key} className="live-row">
              <div style={{ width: "100%" }}>
                <strong>
                  {c.name}: {c.score.toFixed(0)} / 100 <small>· {Math.round(c.weight)}% of your score</small>
                </strong>
                <div role="progressbar" aria-label={c.name} aria-valuenow={c.score} aria-valuemin={0} aria-valuemax={100} style={{ height: 8, background: "#263345", margin: "10px 0" }}>
                  <div style={{ width: `${c.score}%`, height: 8, background: c.score < 25 ? "#fb7185" : c.score < 50 ? "#fb923c" : c.score < 75 ? "#eac75f" : "#55d5ad" }} />
                </div>
                <p>{factorHelp[c.key] ?? (isDebug() ? c.explanation : "")}</p>
                {isDebug() && <small>{c.explanation}</small>}
              </div>
            </article>
          ))}
        </details>
      )}
      {!dirty && !(scoreIsObserved && v1) && (
        <details open={health.score != null}>
          <summary>Score breakdown</summary>
          {health.components.map((c) => (
            <article key={c.name} className="live-row">
              <div style={{ width: "100%" }}>
                <strong>
                  {c.name}: {c.score === null ? "Unavailable" : `${c.score.toFixed(2)} / 100`}
                </strong>
                {c.score !== null && (
                  <div
                    role="progressbar"
                    aria-label={c.name}
                    aria-valuenow={c.score}
                    aria-valuemin={0}
                    aria-valuemax={100}
                    style={{ height: 8, background: "#263345", margin: "10px 0" }}
                  >
                    <div
                      style={{
                        width: `${c.score}%`,
                        height: 8,
                        background:
                          c.score < 25
                            ? "#fb7185"
                            : c.score < 50
                              ? "#fb923c"
                              : c.score < 75
                                ? "#eac75f"
                                : "#55d5ad",
                      }}
                    />
                  </div>
                )}
                <details>
                  <summary>Formula and rationale</summary>
                  <p>{c.formula}</p>
                  <p>{c.reason}</p>
                </details>
              </div>
            </article>
          ))}
        </details>
      )}
      {!dirty && !(scoreIsObserved && v1) && (
        <details>
          <summary>Financial metrics and missing inputs</summary>
          {Object.entries(health.metrics).map(([k, v]) => (
            <p key={k}>
              {k.replace(/_/g, " ")}: {v === null ? "Unknown / not measurable" : String(v)}
            </p>
          ))}
          {health.withheld_reasons.map((w) => (
            <p key={w}>{w}</p>
          ))}
        </details>
      )}
      {!dirty && !(scoreIsObserved && v1) && health.warnings.map((w) => <p key={w}>{w}</p>)}
    </section>
  );
  const resiliencePanel = (
    <section className="live-panel">
      <h2>Economic resilience · Guardian context</h2>
      <p>{context?.note}</p>
      {context?.financial_alerts?.map((a) => (
        <article className="live-alert" key={a.id}>
          <p>{a.cause}</p>
          <p>{a.action}</p>
        </article>
      ))}
      {context?.alerts.length ? (
        context.alerts.map((a) => (
          <article className="live-alert" key={a.id}>
            <h3>{scenarioLabels[a.id] ?? humanize(a.id)}</h3>
            <p>{a.cause}</p>
            <p>{a.action}</p>
            <button
              disabled={busy}
              onClick={() => {
                setScenario(a.scenario);
                void simulate(a.scenario);
              }}
            >
              Test this assumption
            </button>
          </article>
        ))
      ) : (
        <p>
          No personalized economic exposure statement is supported by the current indicators and
          confirmed inputs. This is not a safety guarantee.
        </p>
      )}
    </section>
  );
  const simulationPanel = (
    <section className="live-panel">
      <h2>Try a what-if scenario</h2>
      <p>
        Choose a change and compare your baseline with the hypothetical outcome. Confirm the
        financial inputs below for a complete cash plan.
      </p>
      {error && errorScope === "simulation" && <ErrorSummary message={error} />}
      <select
        aria-label="Stress scenario"
        disabled={busy || !context}
        value={scenario.type}
        onChange={(e) => setScenario((s) => ({ ...s, type: e.target.value }))}
        style={{ background: "#162032", padding: 10 }}
      >
        {[
          "essential_cost_increase",
          "cash_expense_increase",
          "income_reduction",
          "income_interruption",
          "missed_paycheck",
          "emergency_expense",
          "variable_rate_payment",
          "delayed_paycheck",
          "fixed_bill_increase",
          "savings_transfer",
        ].map((s) => (
          <option key={s} value={s}>
            {scenarioLabels[s] ?? humanize(s)}
          </option>
        ))}
      </select>
      <div className="live-grid">
        {["essential_cost_increase", "cash_expense_increase", "income_reduction"].includes(
          scenario.type,
        ) && (
          <label>
            Percentage assumption
            <input
              aria-label="Stress percentage"
              disabled={busy || !context}
              type="number"
              min="0"
              max="100"
              value={Number(scenario.fraction ?? 0.1) * 100}
              onChange={(e) =>
                setScenario((s) => ({ ...s, fraction: Number(e.target.value) / 100 }))
              }
            />
          </label>
        )}
        {[
          "emergency_expense",
          "variable_rate_payment",
          "fixed_bill_increase",
          "savings_transfer",
        ].includes(scenario.type) && (
          <label>
            Dollar assumption
            <input
              aria-label="Stress amount"
              disabled={busy || !context}
              type="number"
              min="0"
              value={scenario.amount ?? 1000}
              onChange={(e) => setScenario((s) => ({ ...s, amount: Number(e.target.value) }))}
            />
          </label>
        )}
        {scenario.type === "delayed_paycheck" && (
          <label>
            Delay days
            <input
              aria-label="Delay days"
              disabled={busy || !context}
              type="number"
              min="1"
              max="90"
              value={scenario.delay_days ?? 7}
              onChange={(e) => setScenario((s) => ({ ...s, delay_days: Number(e.target.value) }))}
            />
          </label>
        )}
      </div>
      <button disabled={busy || !context} onClick={() => void simulate()}>
        {busy && errorScope === "simulation"
          ? "Comparing scenarios..."
          : "Run hypothetical scenario"}
      </button>
      {simulation && (
        <>
          <p>{simulation.note}</p>
          <p>
            Plan coverage: {simulation.after.cash_plan.status}. {simulation.after.cash_plan.note}
          </p>
          <div className="live-grid">
            <p>
              Ending checking change
              <strong className="live-value">{currency(simulation.ending_checking_change)}</strong>
            </p>
            <p>
              Net worth change
              <strong className="live-value">{currency(simulation.net_worth_change)}</strong>
            </p>
            <p>
              Score: {simulation.before.health.score ?? "withheld"} →{" "}
              {simulation.after.health.score ?? "withheld"}
            </p>
          </div>
          <CashChart result={simulation} />
          <p>
            Minimum checking: {currency(simulation.before.cash_plan.minimum_checking)} →{" "}
            {currency(simulation.after.cash_plan.minimum_checking)}
          </p>
          <p>
            Emergency months: {simulation.before.health.metrics.emergency_months ?? "unknown"} →{" "}
            {simulation.after.health.metrics.emergency_months ?? "unknown"}
          </p>
          {simulation.score_changes.map((c, i) => (
            <p key={"change-" + i}>
              {c.component}: {c.before ?? "withheld"} → {c.after ?? "withheld"}. {c.explanation}
            </p>
          ))}
          {simulation.after.guardian_alerts.map((a, i) => (
            <p key={i} className="live-warning">
              {a.cause}
            </p>
          ))}
        </>
      )}
    </section>
  );
  const chatPanel = (
    <section className="live-panel">
      <h2>Ask FinPilot with this assessment</h2>
      {error && errorScope === "chat" && <ErrorSummary message={error} />}
      <textarea
        aria-label="Financial question"
        disabled={busy || !context}
        value={question}
        onChange={(e) => setQuestion(e.target.value)}
        placeholder="What does inflation mean for me?"
        style={{ width: "100%", background: "#162032", color: "white", padding: 12 }}
      />
      <button disabled={busy} onClick={() => void chat()}>
        Ask with confirmed inputs
      </button>
      {delivery && <DeliveryStatus delivery={delivery} />}
      {answer && <ChatRichText content={answer} />}
    </section>
  );
  const panelByName: Record<string, React.ReactNode> = {
    simulation: simulationPanel,
    inputs: inputPanel,
    health: healthPanel,
    resilience: resiliencePanel,
    economy: economyPanel,
    chat: chatPanel,
    cut: cutPanel,
  };
  // Each page shows only what belongs to it (previously all four pages repeated the same panels).
  const panelOrder =
    page === "Digital Twin"
      ? ["cut", "simulation", "inputs", "resilience"]
      : page === "Health Score"
        ? ["health", "inputs"]
        : page === "AI Co-Pilot"
          ? ["chat", "inputs"]
          : ["economy", "resilience"];
  return (
    <div className="live-finance">
      <section className="welcome">
        <div>
          <span className="eyebrow">Financial planning</span>
          <h1>{page}</h1>
          <p>
            {page === "Digital Twin"
              ? "Explore a decision before you make it. Your bank accounts stay unchanged."
              : page === "Health Score"
                ? "Understand your score, confirm your inputs and see what can improve."
                : page === "Economic Lab"
                  ? "Current economic signals and what they could mean for your finances."
                  : "Ask questions grounded in your accounts and confirmed financial inputs."}
          </p>
        </div>
      </section>
      {Boolean(context?.data_notices?.length) && (
        <ReliabilityNotices groups={[context?.data_notices ?? []]} />
      )}
      {error && errorScope === "loading" && (
        <p className="live-warning" role="alert">
          {error} <button onClick={() => setAttempt((n) => n + 1)}>Try again</button>
        </p>
      )}
      {!context && !error && (
        <div role="status" aria-busy="true">
          <p className="skeleton-label">Loading economic evidence and profile…</p>
          <div className="skeleton skeleton-panel" />
        </div>
      )}
      {panelOrder.map((name) => (
        <div key={name}>{panelByName[name]}</div>
      ))}
    </div>
  );
}
