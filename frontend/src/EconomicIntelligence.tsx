import { useEffect, useState } from "react";
import "./connected.css";
import ReliabilityNotices from './ReliabilityNotices';
import { API_BASE } from './api';
import type { Notice } from './api';

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
  score_changes: { component: string; before: number | null; after: number | null; difference: number | null; explanation: string }[];
  ending_checking_change: number;
  net_worth_change: number;
  note: string;
};
const currency = (n: number) => n.toLocaleString("en-US", { style: "currency", currency: "USD" });
async function request<T>(path: string, body?: object, signal?: AbortSignal): Promise<T> {
  const response = await fetch(API_BASE + "/api/" + path, {
    signal,
    cache: 'no-store',
    method: body ? "POST" : "GET",
    headers: body ? { "Content-Type": "application/json" } : undefined,
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!response.ok) {
    const detail = await response.json().catch(() => ({}));
    throw new Error(typeof detail.detail === 'string' ? detail.detail : `Request failed (${response.status}). Check confirmed amounts and required inputs.`);
  }
  return response.json() as Promise<T>;
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
  const [facts, setFacts] = useState<Facts>({ bills_complete: false, debt_complete: false });
  const [context, setContext] = useState<Context | null>(null);
  const [error, setError] = useState("");
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
    request<Context>("resilience", { facts: {} }, controller.signal)
      .then(setContext)
      .catch((e) => {
        if (!controller.signal.aborted) setError(e.message);
      });
    return () => controller.abort();
  }, []);
  const assess = async () => {
    setBusy(true);
    setError("");
    setSimulation(null);
    try {
      setContext(await request<Context>("resilience", { facts: payload() }));
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };
  const simulate = async (chosen = scenario) => {
    setBusy(true);
    setError("");
    try {
      const confirmed = payload();
      const [result, updated] = await Promise.all([
        request<Simulation>("economic-simulate", { facts: confirmed, scenario: chosen }),
        request<Context>("resilience", { facts: confirmed })
      ]);
      setSimulation(result); setContext(updated);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };
  const chat = async () => {
    if (!question.trim()) return;
    setBusy(true);
    setError("");
    try {
      const r = await request<{ reply: string }>("chat", {
        financial_facts: payload(),
        messages: [{ role: "user", content: question }],
      });
      setAnswer(r.reply);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };
  const economy = context?.economic_conditions,
    health = context?.baseline_health;
  return (
    <div className="live-finance">
      <section className="welcome">
        <div>
          <span className="eyebrow">Versioned financial intelligence</span>
          <h1>{page}</h1>
          <p>
            Personal assessment, observed economic conditions and hypothetical stress plans remain
            separate.
          </p>
        </div>
      </section>
      {context && <ReliabilityNotices groups={[context.data_notices ?? []]} />}
      {error && (
        <p className="live-warning" role="alert">
          {error}
        </p>
      )}
      {!context && !error && <p role="status">Loading economic evidence and profile…</p>}
      {economy && (
        <section className="live-panel">
          <h2>Economic conditions · {economy.as_of}</h2>
          <strong className="live-value">{economy.status}</strong>
          <p>{economy.method}</p>
          <p>
            Pressure breadth: {economy.pressure_breadth_index ?? "Unavailable"} / 100. This is
            signal breadth, not a probability or a personal score.
          </p>
          <div className="live-grid">
            {[
              ["Headline CPI YoY (%)", economy.features.CPIAUCSL_yoy_pct],
              ["Core CPI YoY (%)", economy.features.CPILFESL_yoy_pct],
              ["PCE YoY (%)", economy.features.PCEPI_yoy_pct],
              ["Unemployment (%)", economy.indicators.find((i) => i.id === "UNRATE")?.value],
              ["Federal funds (%)", economy.features.policy_rate_pct],
              ["10y minus 2y (pp)", economy.features.yield_spread_pp],
              ["Realized volatility (%)", economy.features.realized_vol20_annualized_pct],
              ["High-yield spread (%)", economy.features.credit_spread_pct],
            ].map(([label, value]) => (
              <article className="live-panel" key={String(label)}>
                <p>{label}</p>
                <strong className="live-value">
                  {typeof value === "number" ? value.toFixed(2) : "Unavailable"}
                </strong>
              </article>
            ))}
          </div>
          <div className="live-grid">
            {economy.dimensions.map((d) => (
              <article className="live-panel" key={d.name}>
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
                      <td>{i.initial_release_date ?? 'Unknown'}</td>
                      <td>
                        {i.frequency} · {i.age_days} days old {i.stale ? "· STALE / excluded" : ""}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {Object.entries(economy.provider_errors).map(([k, v]) => (
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
      )}
      <section className="live-panel">
        <h2>Confirm financial inputs</h2>
        <p>
          Balances come from your scoped bank profile. Confirm take-home income and cash budgets;
          missing values remain unknown. Essential/discretionary amounts include their scheduled
          non-debt bills but exclude debt payments and savings transfers.
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
                onChange={(e) => setFacts((f) => ({ ...f, [key]: e.target.value }))}
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
            </label>
          ))}
        </div>
        <p>
          <label>
            <input
              type="checkbox"
              checked={Boolean(facts.bills_complete)}
              onChange={(e) => setFacts((f) => ({ ...f, bills_complete: e.target.checked }))}
            />{" "}
            I confirm upcoming bills are complete for this assessment.
          </label>
        </p>
        <p>
          <label>
            <input
              type="checkbox"
              checked={Boolean(facts.debt_complete)}
              onChange={(e) => setFacts((f) => ({ ...f, debt_complete: e.target.checked }))}
            />{" "}
            I confirm debt-payment information is complete, including confirmed zero debt if
            applicable.
          </label>
        </p>
        <button disabled={busy} onClick={assess}>
          Calculate assessment
        </button>
        <p><label><input type="checkbox" checked={Boolean(facts.income_history_complete)} onChange={e => setFacts(f => ({ ...f, income_history_complete: e.target.checked }))} /> Classified income history covers complete months; calculate variability only if six months are available.</label></p>
      </section>
      {health && (
        <section className="live-panel">
          <h2>FinPilot personal financial health · v2</h2>
          <strong className="live-value">
            {health.score === null
              ? "Score withheld — confirmation needed"
              : `${health.score.toFixed(2)} / 100`}
          </strong>
          <p>
            {health.completeness.available_components} / {health.completeness.required_components}{" "}
            components supported. Equal provisional weights; not a CFPB or credit score.
          </p>
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
                    <div style={{ width: `${c.score}%`, height: 8, background: "#00e5c3" }} />
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
          {health.warnings.map((w) => (
            <p key={w}>{w}</p>
          ))}
        </section>
      )}
      <section className="live-panel">
        <h2>Economic resilience · Guardian context</h2>
        <p>{context?.note}</p>
        {context?.financial_alerts?.map(a => <article className="live-alert" key={a.id}><p>{a.cause}</p><p>{a.action}</p></article>)}
        {context?.alerts.length ? (
          context.alerts.map((a) => (
            <article className="live-alert" key={a.id}>
              <h3>{a.id.replace(/_/g, " ")}</h3>
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
      <section className="live-panel">
        <h2>Economic stress simulation</h2>
        <select
          aria-label="Stress scenario"
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
              {s.replace(/_/g, " ")}
            </option>
          ))}
        </select>
        <div className="live-grid">
          <label>
            Percentage assumption
            <input
              aria-label="Stress percentage"
              type="number"
              min="0"
              max="100"
              value={Number(scenario.fraction ?? 0.1) * 100}
              onChange={(e) =>
                setScenario((s) => ({ ...s, fraction: Number(e.target.value) / 100 }))
              }
            />
          </label>
          <label>
            Dollar assumption
            <input
              aria-label="Stress amount"
              type="number"
              min="0"
              value={scenario.amount ?? 1000}
              onChange={(e) => setScenario((s) => ({ ...s, amount: Number(e.target.value) }))}
            />
          </label>
          <label>
            Delay days
            <input
              aria-label="Delay days"
              type="number"
              min="1"
              max="90"
              value={scenario.delay_days ?? 7}
              onChange={(e) => setScenario((s) => ({ ...s, delay_days: Number(e.target.value) }))}
            />
          </label>
        </div>
        <button disabled={busy} onClick={() => void simulate()}>
          Run hypothetical scenario
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
                <strong className="live-value">
                  {currency(simulation.ending_checking_change)}
                </strong>
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
            {simulation.score_changes.map((c, i) => <p key={'change-'+i}>{c.component}: {c.before ?? 'withheld'} → {c.after ?? 'withheld'}. {c.explanation}</p>)}
            {simulation.after.guardian_alerts.map((a, i) => (
              <p key={i} className="live-warning">
                {a.cause}
              </p>
            ))}
          </>
        )}
      </section>
      <section className="live-panel">
        <h2>Ask FinPilot with this assessment</h2>
        <textarea
          aria-label="Financial question"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="What does inflation mean for me?"
          style={{ width: "100%", background: "#162032", color: "white", padding: 12 }}
        />
        <button disabled={busy} onClick={() => void chat()}>
          Ask with confirmed inputs
        </button>
        {answer && <p style={{ whiteSpace: "pre-wrap" }}>{answer}</p>}
      </section>
    </div>
  );
}
