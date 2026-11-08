import { useEffect, useRef, useState } from "react";
import { post, type Alert, type Forecast, type SimulationResult, type SpendingCut } from "./api";
import {
  alertFacts, describeCut, eventShort, eventText, fmtDate, fmtDateLong, forecastEvents, isDebug, methodLabel, money,
  moneyShort, niceTicks, plainAssumptions, sourceLabel, type ForecastEvent,
} from "./dashboardLogic";

export { fmtDate, fmtDateLong, isDebug, money, sourceLabel };

// Plain-language descriptions of the health-score factors (the backend sends formulas).
export const factorHelp: Record<string, string> = {
  cash_flow_stability: "How your monthly income compares with your monthly expenses.",
  emergency_savings: "How many months of expenses your cash could cover. Six months earns a full score.",
  debt_management: "Your monthly debt payments as a share of your income. Lower is better.",
  spending_discipline: "How your variable spending compares with your monthly budget.",
  payment_readiness: "Whether your checking balance covers next month's scheduled bills.",
};

// ---------- loading states ----------
export function PageSkeleton({ slow, label = "Loading your financial snapshot…" }: { slow: boolean; label?: string }) {
  return (
    <div className="live-finance" role="status" aria-busy="true">
      <p className="skeleton-label">{label}</p>
      {slow && (
        <p className="live-warning" role="alert">
          Still working — the demo server may be waking up, which can take up to a minute. Your data will
          appear automatically.
        </p>
      )}
      <div className="skeleton skeleton-title" />
      <div className="live-grid account-summary">
        {Array.from({ length: 6 }, (_, i) => (
          <div className="skeleton skeleton-tile" key={i} />
        ))}
      </div>
      <div className="skeleton skeleton-panel" />
    </div>
  );
}

// ---------- scenario results ----------
export function ScenarioResultView({
  result,
  buffer,
  scenario,
}: {
  result: SimulationResult;
  buffer: number | null;
  scenario?: SpendingCut;
}) {
  const b = result.baseline, s = result.scenario;
  const low = s.projected_low?.balance ?? s.end_balance;
  const rows: [string, string, string][] = [
    [
      "Lowest balance",
      b.projected_low ? `${money(b.projected_low.balance)} · ${fmtDate(b.projected_low.date)}` : "—",
      s.projected_low ? `${money(s.projected_low.balance)} · ${fmtDate(s.projected_low.date)}` : "—",
    ],
    ["Ending balance", money(b.end_balance), money(s.end_balance)],
    ["Health score", b.health_score.toFixed(1), s.health_score.toFixed(1)],
  ];
  // Never invent a buffer: without a known one we only report the numbers.
  const verdict =
    buffer == null
      ? { ok: true, text: `Your lowest balance moves from ${money(b.projected_low?.balance ?? b.end_balance)} to ${money(low)}.` }
      : low >= buffer
        ? { ok: true, text: `This change keeps checking above your ${money(buffer)} safety buffer.` }
        : { ok: false, text: `Checking would still dip below your ${money(buffer)} safety buffer.` };
  return (
    <div className="scenario-result" role="status">
      {scenario && <p className="scenario-for">Result for: {describeCut(scenario)}</p>}
      <p className={verdict.ok ? "scenario-verdict ok" : "scenario-verdict warn"}>{verdict.text}</p>
      <table>
        <thead>
          <tr>
            <th scope="col">Outcome</th>
            <th scope="col">Today's plan</th>
            <th scope="col">With this change</th>
          </tr>
        </thead>
        <tbody>
          {rows.map(([label, before, after]) => (
            <tr key={label}>
              <th scope="row">{label}</th>
              <td>{before}</td>
              <td>
                <strong>{after}</strong>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      <small>Hypothetical only. Your accounts are not changed.</small>
    </div>
  );
}

type RunState = { status: "idle" | "loading" | "done" | "error"; result?: SimulationResult; error?: string; scenario?: SpendingCut };
function useScenarioRun() {
  const [run, setRun] = useState<RunState>({ status: "idle" });
  const latest = useRef(0);
  const start = (scenario: SpendingCut) => {
    const id = ++latest.current; // ignore answers to an older submission
    setRun({ status: "loading", scenario });
    post<SimulationResult>("simulate", { scenario })
      .then((result) => latest.current === id && setRun({ status: "done", result, scenario }))
      .catch((e) => latest.current === id && setRun({ status: "error", error: String(e.message), scenario }));
  };
  return { run, start, reset: () => { latest.current += 1; setRun({ status: "idle" }); } };
}

function TestFix({ scenario, buffer }: { scenario: SpendingCut; buffer: number | null }) {
  const { run, start, reset } = useScenarioRun();
  return (
    <div className="test-fix">
      <p>
        <strong>Suggested fix:</strong> {describeCut(scenario)}.
      </p>
      {(run.status === "idle" || run.status === "loading") && (
        <button className="primary" disabled={run.status === "loading"} onClick={() => start(scenario)}>
          {run.status === "loading" ? "Testing…" : "Test this fix"}
        </button>
      )}
      {run.status === "error" && (
        <p className="live-warning" role="alert">
          {run.error} <button onClick={() => start(scenario)}>Try again</button>
        </p>
      )}
      {run.status === "done" && run.result && (
        <>
          <ScenarioResultView result={run.result} buffer={buffer} />
          <button onClick={reset}>Hide result</button>
        </>
      )}
    </div>
  );
}

/** Digital Twin: try any spending cut (not only the suggested one). */
export function SpendingCutSimulator({ defaults, buffer }: { defaults?: SpendingCut | null; buffer: number | null }) {
  const [amount, setAmount] = useState(String(defaults?.reduction_amount ?? 150));
  const [days, setDays] = useState(String(defaults?.horizon_days ?? 10));
  const touched = useRef(false);
  useEffect(() => {
    // Late-arriving suggestions must never overwrite what the user has already typed.
    if (defaults && !touched.current) {
      setAmount(String(defaults.reduction_amount));
      setDays(String(defaults.horizon_days));
    }
  }, [defaults?.reduction_amount, defaults?.horizon_days]);
  const { run, start, reset } = useScenarioRun();
  const a = Number(amount), d = Number(days);
  const valid = amount.trim() !== "" && Number.isFinite(a) && a > 0 && a <= 100000 && Number.isInteger(d) && d >= 1 && d <= 90;
  const edit = (set: (v: string) => void) => (e: { target: { value: string } }) => {
    touched.current = true;
    set(e.target.value);
    if (run.status !== "idle") reset(); // a result always describes the inputs that produced it
  };
  return (
    <section className="live-panel">
      <h2>Test a spending cut</h2>
      <p>See how spending less over a few days changes your lowest balance. Your accounts stay unchanged.</p>
      <form
        className="cut-form"
        noValidate
        onSubmit={(e) => {
          e.preventDefault();
          if (valid) start({ type: "spending_cut", reduction_amount: a, horizon_days: d });
        }}
      >
        <label>
          Amount to cut (USD)
          <input type="number" inputMode="decimal" min="0.01" max={100000} step="any" value={amount} onChange={edit(setAmount)} aria-invalid={!valid} aria-describedby="cut-help" />
        </label>
        <label>
          Over how many days (1–90)
          <input type="number" inputMode="numeric" min={1} max={90} step={1} value={days} onChange={edit(setDays)} aria-invalid={!valid} aria-describedby="cut-help" />
        </label>
        <button className="primary" type="submit" disabled={!valid || run.status === "loading"}>
          {run.status === "loading" ? "Running…" : "Run spending-cut scenario"}
        </button>
      </form>
      <small id="cut-help" aria-live="polite">
        {valid ? "" : "Enter an amount above $0 and a period from 1 to 90 days."}
      </small>
      {run.status === "error" && (
        <p className="live-warning" role="alert">
          {run.error}
        </p>
      )}
      {run.status === "done" && run.result && <ScenarioResultView result={run.result} buffer={buffer} scenario={run.scenario} />}
    </section>
  );
}

// ---------- Guardian ----------
export function GuardianPanel({ alerts, buffer, title = "Guardian · 30-day outlook" }: { alerts: Alert[]; buffer: number | null; title?: string }) {
  return (
    <section className="live-panel">
      <h2>{title}</h2>
      {alerts.length ? (
        alerts.map((a) => (
          <article className={`live-alert sev-${a.severity}`} key={a.id}>
            <h3>
              {a.title} <span className={`sev-badge sev-${a.severity}`}>{a.severity}</span>
            </h3>
            <p>{a.cause}</p>
            {alertFacts(a).length > 0 && (
              <ul className="alert-facts">
                {alertFacts(a).map((f) => (
                  <li key={f}>{f}</li>
                ))}
              </ul>
            )}
            <p>{a.recommended_action}</p>
            {a.suggested_scenario && <TestFix scenario={a.suggested_scenario} buffer={buffer} />}
          </article>
        ))
      ) : (
        <p>No configured rules triggered. This does not guarantee financial safety.</p>
      )}
    </section>
  );
}

// ---------- chart ----------
function useCompact() {
  const query = "(max-width: 640px)";
  const [compact, setCompact] = useState(() => window.matchMedia(query).matches);
  useEffect(() => {
    const m = window.matchMedia(query);
    const on = () => setCompact(m.matches);
    m.addEventListener("change", on);
    return () => m.removeEventListener("change", on);
  }, []);
  return compact;
}

export function BalanceChart({ forecast, events }: { forecast: Forecast; events: ForecastEvent[] }) {
  const compact = useCompact();
  const rows = forecast.series;
  if (!rows.length) return <p>No forecast available.</p>;
  const buffer = forecast.safety_buffer;
  const W = compact ? 480 : 920, H = compact ? 340 : 330;
  const L = compact ? 58 : 74, R = 16, T = 52, B = 38;
  const fs = compact ? 15 : 12;
  const values = rows.flatMap((r) => [r.low, r.high, r.projected_balance]);
  const ticks = niceTicks(Math.min(...values, buffer), Math.max(...values, buffer));
  const d0 = ticks[0], d1 = ticks[ticks.length - 1];
  const x = (i: number) => L + (i * (W - L - R)) / Math.max(1, rows.length - 1);
  const y = (v: number) => T + (H - T - B) * (1 - (v - d0) / Math.max(1, d1 - d0));
  const path = (k: "low" | "high" | "projected_balance") => rows.map((r, i) => `${x(i)},${y(r[k])}`).join(" ");
  const band = `${path("high")} ${rows.map((r, i) => `${x(i)},${y(r.low)}`).reverse().join(" ")}`;
  const minIdx = rows.reduce((m, r, i) => (r.projected_balance < rows[m].projected_balance ? i : m), 0);
  const min = rows[minIdx];
  const below = min.projected_balance < buffer;
  const step = compact ? 14 : 7;
  const last = rows.length - 1;
  const dateIdx = rows.map((_, i) => i).filter((i) => i === last || (i % step === 0 && last - i >= step * 0.75));
  const biggest = [...events].sort((a, b) => Math.abs(b.amount) - Math.abs(a.amount)).slice(0, compact ? 1 : 3);
  const anchor = x(minIdx) > W * 0.62 ? "end" : "start";
  const bufferLabelBelow = y(buffer) < T + 18; // keep the label clear of the event labels above the plot
  // On phones the buffer label sits below its line, so the low-point label goes above its marker.
  const lowLabelAbove = y(min.projected_balance) + 24 > H - B || (compact && below);
  const summary = `Checking balance forecast for ${forecast.days} days. Lowest projected balance ${money(min.projected_balance)} on ${fmtDate(min.date)}${below ? `, below the ${money(buffer)} safety buffer` : ""}. Daily values follow in a table.`;
  return (
    <figure className="balance-chart">
      <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label={summary}>
        {ticks.map((v) => (
          <g key={v}>
            <line x1={L} x2={W - R} y1={y(v)} y2={y(v)} stroke="#2a3547" />
            <text x={L - 8} y={y(v) + 4} textAnchor="end" fill="#94a3b8" fontSize={fs}>
              {moneyShort(v)}
            </text>
          </g>
        ))}
        <rect x={L} y={y(buffer)} width={W - L - R} height={Math.max(0, y(d0) - y(buffer))} fill="#fb7185" opacity="0.07" />
        <polygon points={band} fill="#00e5c3" opacity="0.1" />
        <line x1={L} x2={W - R} y1={y(buffer)} y2={y(buffer)} stroke="#fb7185" strokeDasharray="6 4" />
        <text
          x={W - R}
          y={bufferLabelBelow || compact ? y(buffer) + 16 : y(buffer) - 6}
          textAnchor="end"
          fill="#fda4af"
          fontSize={fs}
        >
          {compact ? `${moneyShort(buffer)} buffer` : `${money(buffer)} safety buffer`}
        </text>
        {biggest.map((e, k) => {
          const i = rows.findIndex((r) => r.date === e.date);
          return (
            <g key={e.date}>
              <line x1={x(i)} x2={x(i)} y1={T - 6} y2={H - B} stroke="#64748b" strokeDasharray="2 4" opacity="0.6" />
              <text x={x(i)} y={T - 12 - (k % 2) * 15} textAnchor={x(i) > W * 0.7 ? "end" : "start"} fill="#cbd5e1" fontSize={compact ? 14 : 11}>
                {eventShort(e)}
              </text>
            </g>
          );
        })}
        <polyline points={path("projected_balance")} fill="none" stroke="#00e5c3" strokeWidth="3" strokeLinejoin="round" />
        <circle cx={x(minIdx)} cy={y(min.projected_balance)} r="6" fill={below ? "#fb7185" : "#00e5c3"} stroke="#0b0e14" strokeWidth="2" />
        <text
          x={x(minIdx) + (anchor === "end" ? -10 : 10)}
          y={lowLabelAbove ? y(min.projected_balance) - 12 : y(min.projected_balance) + 22}
          textAnchor={anchor}
          fill={below ? "#fda4af" : "#99f6e4"}
          fontSize={fs}
          fontWeight="600"
        >
          Lowest: {fmtDate(min.date)} · {money(min.projected_balance)}
        </text>
        {dateIdx.map((i) => (
          <text key={i} x={x(i)} y={H - 12} textAnchor={i === last ? "end" : "middle"} fill="#94a3b8" fontSize={fs}>
            {fmtDate(rows[i].date)}
          </text>
        ))}
        {rows.map((r, i) => (
          <circle key={r.date} cx={x(i)} cy={y(r.projected_balance)} r={compact ? 9 : 6} fill="transparent">
            <title>{`${fmtDate(r.date)}: ${money(r.projected_balance)} (stress range ${money(r.low)} to ${money(r.high)})`}</title>
          </circle>
        ))}
      </svg>
      <figcaption>
        Teal line: projected checking balance. Shaded band: a stress range, from a high-spending case up to a case
        with no variable spending. It is not a statistical confidence interval. Dashed line: your safety buffer.
      </figcaption>
    </figure>
  );
}

// ---------- forecast card ----------
export function ForecastPanel({
  days,
  setDays,
  forecast,
  loading,
  error,
  retry,
  startBalance,
  bills,
  showShortfall,
}: {
  days: number;
  setDays: (n: number) => void;
  forecast: Forecast | null;
  loading: boolean;
  error: string;
  retry: () => void;
  startBalance: number;
  bills: { name: string; amount: number; due_date: string }[];
  showShortfall: boolean;
}) {
  const events = forecast ? forecastEvents(forecast.series, startBalance, bills) : [];
  const eventByDate = new Map(events.map((e) => [e.date, e]));
  return (
    <section className="live-panel">
      <div className="live-row">
        <h2>Predictive spending & cash flow</h2>
        <div className="live-periods" role="group" aria-label="Forecast horizon">
          {[7, 30, 90].map((n) => (
            <button key={n} aria-pressed={days === n} onClick={() => setDays(n)}>
              {n} days
            </button>
          ))}
        </div>
      </div>
      {error ? (
        <p role="alert">
          {error} <button onClick={retry}>Retry</button>
        </p>
      ) : loading || !forecast ? (
        <div role="status" aria-busy="true">
          <p className="skeleton-label">Calculating {days}-day forecast…</p>
          <div className="skeleton skeleton-chart" />
        </div>
      ) : forecast.status === "abstained" ? (
        <p>No balance path is shown because spending could not be estimated.</p>
      ) : (
        <>
          <p className="forecast-method">
            Based on {methodLabel(forecast.meta.forecast_reliability?.method)}, plus your scheduled income and bills.
            Estimate as of {fmtDateLong(forecast.meta.as_of)}.
          </p>
          <div className="forecast-stats">
            <p>
              <span>Ending checking</span>
              <strong className="live-value">{money(forecast.series.at(-1)?.projected_balance ?? startBalance)}</strong>
            </p>
            <p className={forecast.shortfall ? "stat-warn" : ""}>
              <span>
                Lowest projected checking{forecast.projected_low && <small> · {fmtDate(forecast.projected_low.date)}</small>}
              </span>
              <strong className="live-value">{money(forecast.projected_low?.balance ?? startBalance)}</strong>
            </p>
            <p>
              <span>Safety buffer</span>
              <strong className="live-value">{money(forecast.safety_buffer)}</strong>
            </p>
          </div>
          {forecast.shortfall && showShortfall && (
            <p className="live-warning" role="alert">
              Cash-shortage warning: checking is projected below your safety buffer during this horizon. Review
              scheduled obligations and test optional spending reductions.
            </p>
          )}
          <BalanceChart forecast={forecast} events={events} />
          <details>
            <summary>Forecast assumptions</summary>
            <ul>
              <li>Scheduled income and bills are included on their due dates.</li>
              {plainAssumptions(forecast.assumptions, isDebug()).map((a) => (
                <li key={a}>{a}</li>
              ))}
            </ul>
          </details>
          <details>
            <summary>Daily forecast · {forecast.series.length} days</summary>
            <div className="live-table">
              <table>
                <caption className="visually-hidden">Day-by-day projected checking balance</caption>
                <thead>
                  <tr>
                    <th scope="col">Date</th>
                    <th scope="col">Scheduled income / bills</th>
                    <th scope="col">Variable spending</th>
                    <th scope="col">Checking</th>
                    <th scope="col">Stress case: high spending</th>
                    <th scope="col">Upper bound: no variable spending</th>
                  </tr>
                </thead>
                <tbody>
                  {forecast.series.map((r) => {
                    const e = eventByDate.get(r.date);
                    return (
                      <tr key={r.date}>
                        <td>{fmtDate(r.date)}</td>
                        <td>{e ? eventText(e) : "—"}</td>
                        <td>{money(r.predicted_spend)}</td>
                        <td>{money(r.projected_balance)}</td>
                        <td>{money(r.low)}</td>
                        <td>{money(r.high)}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </details>
        </>
      )}
    </section>
  );
}
