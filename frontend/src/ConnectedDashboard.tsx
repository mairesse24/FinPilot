import { useEffect, useState } from "react";
import { get, type Context, type Dashboard, type Forecast } from "./api";
import "./connected.css";
import ReliabilityNotices from "./ReliabilityNotices";
import type { Notice } from "./api";

const money = (n: number) =>
  new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" }).format(n);

function BalanceChart({ forecast }: { forecast: Forecast }) {
  const rows = forecast.series;
  if (!rows.length) return <p>No forecast available.</p>;
  const values = rows.flatMap((r) => [r.low, r.high, r.projected_balance]);
  const bottom = Math.min(...values, forecast.safety_buffer),
    top = Math.max(...values, forecast.safety_buffer);
  const range = Math.max(1, top - bottom);
  const x = (i: number) => 90 + (i * 790) / Math.max(1, rows.length - 1);
  const y = (v: number) => 225 - ((v - bottom) / range) * 195;
  const line = (key: "low" | "high" | "projected_balance") =>
    rows.map((r, i) => `${x(i)},${y(r[key])}`).join(" ");
  const area =
    line("high") +
    " " +
    rows
      .map((r, i) => `${x(i)},${y(r.low)}`)
      .reverse()
      .join(" ");
  return (
    <figure>
      <svg
        viewBox="0 0 920 280"
        role="img"
        aria-label={`Checking balance forecast for ${forecast.days} days with spending stress envelope. The full daily values follow in a table.`}
      >
        {[bottom, (top + bottom) / 2, top].map((v, i) => (
          <g key={i}>
            <line x1="90" x2="880" y1={y(v)} y2={y(v)} stroke="#334155" />
            <text x="2" y={y(v) - 4} fill="#94a3b8" fontSize="12">
              {money(v)}
            </text>
          </g>
        ))}
        <polygon points={area} fill="#00e5c3" opacity="0.12" />
        <polyline points={line("projected_balance")} fill="none" stroke="#00e5c3" strokeWidth="3" />
        <line
          x1="90"
          x2="880"
          y1={y(forecast.safety_buffer)}
          y2={y(forecast.safety_buffer)}
          stroke="#fb7185"
          strokeDasharray="6 4"
        />
        <text x="90" y="260" fill="#94a3b8" fontSize="13">
          {rows[0].date}
        </text>
        <text x="780" y="260" fill="#94a3b8" fontSize="13">
          {rows[rows.length - 1].date}
        </text>
      </svg>
      <figcaption>
        Teal: projected checking. Shaded: spending stress envelope, not a calibrated confidence
        interval. Dashed: chosen safety buffer.
      </figcaption>
    </figure>
  );
}

export default function ConnectedDashboard({ page }: { page: string }) {
  const [days, setDays] = useState(30);
  const [dashboard, setDashboard] = useState<Dashboard | null>(null);
  const [context, setContext] = useState<Context | null>(null);
  const [forecast, setForecast] = useState<Forecast | null>(null);
  const [error, setError] = useState("");
  const [forecastError, setForecastError] = useState("");
  const [retry, setRetry] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    setError("");
    setDashboard(null);
    setContext(null);
    Promise.all([
      get<Dashboard>("dashboard", controller.signal),
      get<Context>("context", controller.signal),
    ])
      .then(([d, c]) => {
        if (controller.signal.aborted) return;
        setDashboard(d);
        setContext(c);
      })
      .catch((e) => {
        if (!controller.signal.aborted) setError(String(e.message));
      });
    return () => controller.abort();
  }, [retry]);
  useEffect(() => {
    const controller = new AbortController();
    setForecast(null);
    setForecastError("");
    get<Forecast>(`forecast?days=${days}`, controller.signal)
      .then(f => { if (!controller.signal.aborted) setForecast(f); })
      .catch((e) => {
        if (!controller.signal.aborted) setForecastError(String(e.message));
      });
    return () => controller.abort();
  }, [days, retry]);
  if (error)
    return (
      <section className="live-panel" role="alert">
        <h1>Dashboard unavailable</h1>
        <p>{error}</p>
        <button onClick={() => setRetry((r) => r + 1)}>Retry</button>
      </section>
    );
  if (!dashboard || !context) return <p role="status">Loading your financial snapshot…</p>;
  const checking = dashboard.accounts
    .filter((a) => a.account_type === "checking")
    .reduce((s, a) => s + a.balance, 0);
  const savings = dashboard.accounts
    .filter((a) => a.account_type === "savings")
    .reduce((s, a) => s + a.balance, 0);
  const alerts = dashboard.active_alerts.filter(a => a.rule !== 'forecast_uncertain');
  return (
    <div className="live-finance">
      <section className="welcome">
        <div>
          <span className="eyebrow">
            {context.as_of} · {context.data_source}
          </span>
          <h1>{page === "Overview" ? `Welcome, ${context.user.name}` : page}</h1>
          <p>Synthetic financial prototype · {context.user.id} · not financial advice</p>
        </div>
        <button onClick={() => setRetry((r) => r + 1)}>Reload analysis</button>
      </section>
      {context.loaded_at && (
        <p>
          Bank snapshot loaded {new Date(context.loaded_at).toLocaleString()}.
        </p>
      )}
      <ReliabilityNotices groups={[
        context.notices ?? [], dashboard.meta.notices ?? [], forecast?.meta.notices ?? [],
        ...(!forecast?.meta.notices?.length && forecast?.status === "abstained" ? [[{
          code: "forecast_unavailable", context: "analysis", category: "critical",
          message: "Forecast abstained: more history is needed. Future balances are unavailable.",
          technical_detail: forecast.meta.warning ?? "No observed history."
        } as Notice]] : [])
      ]} metas={[dashboard.meta, ...(forecast ? [forecast.meta] : [])]} />
      {page !== "Forecasts" && (
        <>
          <section className="live-grid">
            {[
              ["Net worth", dashboard.net_worth],
              ["Checking", checking],
              ["Savings", savings],
              ["Liabilities owed", dashboard.liabilities],
              ["Inflow · last 30 days", dashboard.income_30d],
              ["Spending · last 30 days", dashboard.spending_30d],
            ].map(([label, value]) => (
              <article className="live-panel" key={String(label)}>
                <p>{label}</p>
                <strong className="live-value">{money(Number(value))}</strong>
              </article>
            ))}
          </section>
          <section className="live-grid two">
            <article className="live-panel">
              <h2>Accounts</h2>
              {dashboard.accounts.length ? (
                dashboard.accounts.map((a) => (
                  <div className="live-row" key={a.id}>
                    <span>
                      {a.name}
                      <small>
                        {a.account_type.replace("_", " ")}
                        {["credit_card", "loan"].includes(a.account_type) ? " · owed" : ""}
                      </small>
                    </span>
                    <strong>{money(a.balance)}</strong>
                  </div>
                ))
              ) : (
                <p>No imported accounts.</p>
              )}
            </article>
            <article className="live-panel">
              <h2>Upcoming bills · 14 days</h2>
              {dashboard.upcoming_bills.length ? (
                dashboard.upcoming_bills.map((b, i) => (
                  <div className="live-row" key={i}>
                    <span>
                      {b.name}
                      <small>{b.due_date}</small>
                    </span>
                    <strong>{money(b.amount)}</strong>
                  </div>
                ))
              ) : (
                <p>
                  No bills provided in this window. This does not establish that no bills are owed.
                </p>
              )}
            </article>
          </section>
          <section className="live-grid two">
            <article className="live-panel">
              <h2>Spending by category · 30 days</h2>
              {dashboard.by_category.map((c) => (
                <div className="live-row" key={c.category}>
                  <span>{c.category}</span>
                  <strong>{money(c.amount)}</strong>
                </div>
              ))}
            </article>
            <article className="live-panel">
              <h2>Financial health · legacy v1</h2>
              <strong className="live-value">{dashboard.health_score.toFixed(1)} / 100</strong>
              <p>Internal heuristic, not a credit score. Data gaps can affect this assessment.</p>
            </article>
          </section>
          <section className="live-panel">
            <h2>Guardian · 30-day outlook</h2>
            {alerts.length ? (
              alerts.map((a) => (
                <article className="live-alert" key={a.id}>
                  <h3>
                    {a.title} · {a.severity}
                  </h3>
                  <p>{a.cause}</p>
                  <p>{a.recommended_action}</p>
                </article>
              ))
            ) : (
              <p>No configured rules triggered. This does not guarantee financial safety.</p>
            )}
          </section>
        </>
      )}
      <section className="live-panel">
        <div className="live-row">
          <h2>Predictive spending & cash flow</h2>
          <div className="live-periods" aria-label="Forecast horizon">
            {[7, 30, 90].map((n) => (
              <button key={n} aria-pressed={days === n} onClick={() => setDays(n)}>
                {n} days
              </button>
            ))}
          </div>
        </div>
        {forecastError ? (
          <p role="alert">
            {forecastError} <button onClick={() => setRetry((r) => r + 1)}>Retry</button>
          </p>
        ) : !forecast ? (
          <p role="status">Calculating {days}-day forecast…</p>
          ) : forecast.status === "abstained" ? (
            <p>No balance path is shown because spending could not be estimated.</p>
        ) : (
          <>
            <p>
              Estimate method: {forecast.meta.forecast_reliability?.method ?? forecast.meta.source} · As of {forecast.meta.as_of}. Scheduled income and
              bills are combined with predicted variable spending.
            </p>

            <div className="live-grid">
              <p>
                Ending checking
                <strong className="live-value">
                  {money(forecast.series.at(-1)?.projected_balance ?? checking)}
                </strong>
              </p>
              <p>
                Lowest projected checking
                <strong className="live-value">
                  {money(forecast.projected_low?.balance ?? checking)}
                </strong>
                {forecast.projected_low?.date}
              </p>
              <p>
                Safety buffer<strong className="live-value">{money(forecast.safety_buffer)}</strong>
              </p>
            </div>
            {forecast.shortfall && (page === 'Forecasts' || !alerts.some(a => a.rule === 'low_projected_balance' || a.rule === 'low_balance')) && (
              <p className="live-warning" role="alert">
                Cash-shortage warning: checking is projected below your safety buffer during this
                horizon. Review scheduled obligations and test optional spending reductions.
              </p>
            )}
            <BalanceChart forecast={forecast} />
            <details>
              <summary>Forecast assumptions</summary>
              <ul>
                {forecast.assumptions.map((a, i) => (
                  <li key={i}>{a}</li>
                ))}
              </ul>
            </details>
            <details>
              <summary>Daily forecast · {forecast.series.length} days</summary>
              <div className="live-table">
                <table>
                  <thead>
                    <tr>
                      <th>Date</th>
                      <th>Variable spending</th>
                      <th>Checking</th>
                      <th>Low stress</th>
                      <th>High stress</th>
                    </tr>
                  </thead>
                  <tbody>
                    {forecast.series.map((r) => (
                      <tr key={r.date}>
                        <td>{r.date}</td>
                        <td>{money(r.predicted_spend)}</td>
                        <td>{money(r.projected_balance)}</td>
                        <td>{money(r.low)}</td>
                        <td>{money(r.high)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </details>
          </>
        )}
      </section>
    </div>
  );
}
