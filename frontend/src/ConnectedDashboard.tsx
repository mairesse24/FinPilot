import { useState } from "react";
import { type Alert, type Dashboard, type HealthV1, type Notice } from "./api";
import "./connected.css";
import "./design-dashboard.css";
import ReliabilityNotices from "./ReliabilityNotices";
import AccountDetails from "./AccountDetails";
import { useFinance, useHealthScore, useSlow } from "./financeStore";
import { ForecastPanel, GuardianPanel, PageSkeleton, fmtDate, fmtDateLong, money, sourceLabel } from "./dashboardParts";
import LiveTransactionDemo from "./LiveTransactionDemo";

const subtitles: Record<string, string> = {
  Overview: "Your accounts, cash flow and upcoming obligations in one place.",
  "My Finances": "Every account, bill and spending category in one list.",
  Guardian: "Risks found in your next 30 days, and what you can do about them.",
  Forecasts: "How your checking balance is expected to move over the coming weeks.",
};

function ScoreCard({ score, health }: { score: number; health: HealthV1 | null }) {
  const tone = (n: number) => (n < 25 ? "#fb7185" : n < 50 ? "#fb923c" : n < 75 ? "#eac75f" : "#55d5ad");
  return (
    <article className="live-panel score-card">
      <h2>Financial health score</h2>
      <strong className="live-value">{score.toFixed(2)} / 100</strong>
      {health ? (
        <ul className="factor-list" aria-label="What makes up this score">
          {health.components.map((c) => (
            <li key={c.key}>
              <span>
                {c.name} <small>{Math.round(c.weight)}% of score</small>
              </span>
              <span className="factor-bar" aria-hidden="true">
                <span style={{ width: `${c.score}%`, background: tone(c.score) }} />
              </span>
              <strong>{c.score.toFixed(0)}</strong>
            </li>
          ))}
        </ul>
      ) : (
        <p>Estimate based on your available account, spending and payment data.</p>
      )}
      <a className="card-link" href="#/health-score">
        How this score is calculated →
      </a>
    </article>
  );
}

function Tiles({ dashboard, open }: { dashboard: Dashboard; open: (filter: string) => void }) {
  const sum = (type: string) => dashboard.accounts.filter((a) => a.account_type === type).reduce((s, a) => s + a.balance, 0);
  const items = [
    { label: "Net worth", value: dashboard.net_worth, filter: "all", hint: "Assets minus recorded debt" },
    { label: "Checking", value: sum("checking"), filter: "checking", hint: "Every imported checking account" },
    { label: "Savings", value: sum("savings"), filter: "savings", hint: "Every imported savings account" },
    { label: "Loans", value: sum("loan"), filter: "loan", hint: "Outstanding recorded principal" },
    { label: "Credit cards", value: sum("credit_card"), filter: "credit_card", hint: "Recorded card balances owed" },
    { label: "Liabilities owed", value: dashboard.liabilities, filter: "debt", hint: "Loans and credit cards" },
  ];
  return (
    <>
      <section className="live-grid account-summary">
        {items.map((item) => (
          <button className="live-panel account-tile" key={item.label} onClick={() => open(item.filter)}>
            <span>
              <span>{item.label}</span>
              <span aria-hidden="true"> +</span>
            </span>
            <strong className="live-value">{money(item.value)}</strong>
            <small>{item.hint}</small>
          </button>
        ))}
      </section>
      <div className="cash-strip">
        <p>
          Inflow - last 30 days <strong>{money(dashboard.income_30d)}</strong>
        </p>
        <p>
          Spending - last 30 days <strong>{money(dashboard.spending_30d)}</strong>
        </p>
      </div>
    </>
  );
}

function AccountsPanel({ dashboard, open }: { dashboard: Dashboard; open: (filter: string) => void }) {
  return (
    <article className="live-panel">
      <div className="live-row">
        <h2>Accounts</h2>
        <button onClick={() => open("all")}>View all accounts</button>
      </div>
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
            <button aria-label={`View ${a.name}`} onClick={() => open(a.account_type)}>
              {money(a.balance)}
            </button>
          </div>
        ))
      ) : (
        <p>No imported accounts.</p>
      )}
    </article>
  );
}

function BillsPanel({ dashboard }: { dashboard: Dashboard }) {
  return (
    <article className="live-panel">
      <h2>Upcoming bills · 14 days</h2>
      {dashboard.upcoming_bills.length ? (
        dashboard.upcoming_bills.map((b, i) => (
          <div className="live-row" key={i}>
            <span>
              {b.name}
              <small>{fmtDate(b.due_date)}</small>
            </span>
            <strong>{money(b.amount)}</strong>
          </div>
        ))
      ) : (
        <p>No bills provided in this window. This does not establish that no bills are owed.</p>
      )}
    </article>
  );
}

function CategoryPanel({ dashboard }: { dashboard: Dashboard }) {
  const total = dashboard.by_category.reduce((s, c) => s + c.amount, 0) || 1;
  return (
    <article className="live-panel">
      <h2>Spending by category · 30 days</h2>
      {dashboard.by_category.map((c) => (
        <div className="live-row category-row" key={c.category}>
          <span>
            {c.category}
            <span className="category-bar" aria-hidden="true">
              <span style={{ width: `${Math.max(2, (c.amount / total) * 100)}%` }} />
            </span>
          </span>
          <strong>{money(c.amount)}</strong>
        </div>
      ))}
    </article>
  );
}

export default function ConnectedDashboard({ page }: { page: string }) {
  const [days, setDays] = useState(30);
  const [selectedAccounts, setSelectedAccounts] = useState<string | null>(null);
  const f = useFinance(days);
  const { health } = useHealthScore();
  const slow = useSlow(f.coreLoading || f.forecastLoading);
  if (f.coreError)
    return (
      <section className="live-panel" role="alert">
        <h1>Dashboard unavailable</h1>
        <p>{f.coreError}</p>
        <button onClick={f.reload}>Retry</button>
      </section>
    );
  const { dashboard, context } = f;
  if (!dashboard || !context) return <PageSkeleton slow={slow} />;
  const checking = dashboard.accounts.filter((a) => a.account_type === "checking").reduce((s, a) => s + a.balance, 0);
  const alerts: Alert[] = dashboard.active_alerts.filter((a) => a.rule !== "forecast_uncertain");
  // Only a buffer the backend actually reported; never an invented default.
  const alertBuffer = Number(alerts.find((a) => a.numbers?.buffer != null)?.numbers?.buffer);
  const buffer: number | null = f.forecast?.safety_buffer ?? (Number.isFinite(alertBuffer) ? alertBuffer : null);
  const open = (filter: string) => setSelectedAccounts(filter);
  const showTiles = page === "Overview" || page === "My Finances";
  const forecastCard = (
    <ForecastPanel
      days={days}
      setDays={setDays}
      forecast={f.forecast}
      loading={f.forecastLoading}
      error={f.forecastError}
      retry={f.retryForecast}
      startBalance={checking}
      bills={dashboard.upcoming_bills}
      showShortfall={page === "Forecasts" || !alerts.some((a) => a.rule === "low_projected_balance" || a.rule === "low_balance")}
    />
  );
  return (
    <div className="live-finance">
      <AccountDetails selected={selectedAccounts} accounts={dashboard.accounts} close={() => setSelectedAccounts(null)} />
      <section className="welcome">
        <div>
          <span className="eyebrow welcome-meta">
            {fmtDateLong(context.as_of)} · {sourceLabel(context.data_source)}
          </span>
          <h1>{page === "Overview" ? `Welcome, ${context.user.name}` : page}</h1>
          <p>{subtitles[page] ?? subtitles.Overview}</p>
        </div>
        <div className="welcome-actions">
          {page === "Overview" && <LiveTransactionDemo accounts={dashboard.accounts} />}
          <button onClick={f.reload}>Reload analysis</button>
        </div>
      </section>
      {context.loaded_at && <p className="snapshot-time">Last bank-data sync: {new Date(context.loaded_at).toLocaleString()}</p>}
      <ReliabilityNotices
        groups={[
          context.notices ?? [],
          dashboard.meta.notices ?? [],
          f.forecast?.meta.notices ?? [],
          ...(!f.forecast?.meta.notices?.length && f.forecast?.status === "abstained"
            ? [
                [
                  {
                    code: "forecast_unavailable",
                    context: "analysis",
                    category: "critical",
                    message: "Forecast abstained: more history is needed. Future balances are unavailable.",
                    technical_detail: f.forecast.meta.warning ?? "No observed history.",
                  } as Notice,
                ],
              ]
            : []),
        ]}
        metas={[dashboard.meta, ...(f.forecast ? [f.forecast.meta] : [])]}
      />
      {showTiles && <Tiles dashboard={dashboard} open={open} />}
      {(page === "Overview" || page === "Guardian") && <GuardianPanel alerts={alerts} buffer={buffer} title={page === "Guardian" ? "Alerts and suggested fixes" : "Guardian · 30-day outlook"} />}
      {(page === "Overview" || page === "Guardian" || page === "Forecasts") && forecastCard}
      {page === "Overview" && (
        <>
          <section className="live-grid two">
            <AccountsPanel dashboard={dashboard} open={open} />
            <BillsPanel dashboard={dashboard} />
          </section>
          <section className="live-grid two">
            <CategoryPanel dashboard={dashboard} />
            <ScoreCard score={dashboard.health_score} health={health} />
          </section>
        </>
      )}
      {page === "My Finances" && (
        <>
          <section className="live-grid two">
            <AccountsPanel dashboard={dashboard} open={open} />
            <BillsPanel dashboard={dashboard} />
          </section>
          <CategoryPanel dashboard={dashboard} />
        </>
      )}
    </div>
  );
}
