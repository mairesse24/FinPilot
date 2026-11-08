import { useEffect, useMemo, useRef, useState } from "react";
import {
  Activity,
  ArrowDown,
  ArrowUp,
  CircleDollarSign,
  Globe2,
  Landmark,
  MessageSquareText,
  Pause,
  Play,
  ReceiptText,
  ShieldCheck,
  Sparkles,
  WalletCards,
} from "lucide-react";
import { get, type Context, type Dashboard, type Forecast } from "./api";
import ReliabilityNotices from "./ReliabilityNotices";
import "./wrapped.css";

type Economy = {
  as_of: string;
  status: string;
  labels: string[];
  pressure_breadth_index: number | null;
  method: string;
  evidence_quality?: { available_dimensions: number; total_dimensions: number; kind: string };
};

const money = (value: number) =>
  value.toLocaleString("en-US", { style: "currency", currency: "USD" });

const accountTotal = (dashboard: Dashboard, type: string) =>
  dashboard.accounts
    .filter((account) => account.account_type === type)
    .reduce((sum, account) => sum + account.balance, 0);

const SLIDE_DURATION_MS = 7000;

function economicGuidance(economy: Economy | null, dashboard: Dashboard) {
  const guardian = dashboard.active_alerts[0];
  if (guardian) return guardian.recommended_action;
  if (!economy || economy.status === "Insufficient Data")
    return "Keep enough accessible cash for upcoming bills and use the Digital Twin before making a large change.";
  if (economy.status === "Multiple pressure signals" || economy.status === "Mixed Signals")
    return "Preserve your essential-payment buffer and test an income or cost shock in the Digital Twin before adding a new obligation.";
  return "No configured broad pressure pattern is active. Keep your emergency reserve aligned with essential expenses and review conditions as they change.";
}

export default function FinPilotWrapped() {
  const [dashboard, setDashboard] = useState<Dashboard | null>(null);
  const [forecast, setForecast] = useState<Forecast | null>(null);
  const [economy, setEconomy] = useState<Economy | null>(null);
  const [context, setContext] = useState<Context | null>(null);
  const [active, setActive] = useState(0);
  const [autoplayEnabled, setAutoplayEnabled] = useState(true);
  const [holdPaused, setHoldPaused] = useState(false);
  const [timerKey, setTimerKey] = useState(0);
  const [error, setError] = useState("");
  const story = useRef<HTMLDivElement>(null);
  const remainingTime = useRef(SLIDE_DURATION_MS);
  const timerStartedAt = useRef(0);

  useEffect(() => {
    const controller = new AbortController();
    Promise.all([
      get<Dashboard>("dashboard", controller.signal),
      get<Forecast>("forecast?days=30", controller.signal),
      get<Economy>("economy", controller.signal),
      get<Context>("context", controller.signal),
    ])
      .then(([nextDashboard, nextForecast, nextEconomy, nextContext]) => {
        setDashboard(nextDashboard);
        setForecast(nextForecast);
        setEconomy(nextEconomy);
        setContext(nextContext);
      })
      .catch((reason) => {
        if (!controller.signal.aborted)
          setError(reason instanceof Error ? reason.message : "Your snapshot could not be loaded.");
      });
    return () => controller.abort();
  }, []);

  useEffect(() => {
    const root = story.current;
    if (!root) return;
    const observer = new IntersectionObserver(
      (entries) => {
        const visible = entries
          .filter((entry) => entry.isIntersecting)
          .sort((a, b) => b.intersectionRatio - a.intersectionRatio)[0];
        if (visible) setActive(Number((visible.target as HTMLElement).dataset.slide ?? 0));
      },
      { root, threshold: [0.45, 0.7] },
    );
    root.querySelectorAll(".wrapped-slide").forEach((slide) => observer.observe(slide));
    return () => observer.disconnect();
  }, [dashboard]);

  const topCategories = useMemo(
    () => [...(dashboard?.by_category ?? [])].sort((a, b) => b.amount - a.amount).slice(0, 5),
    [dashboard],
  );
  const go = (index: number, restartTimer = true) => {
    story.current?.querySelector<HTMLElement>(`[data-slide="${index}"]`)?.scrollIntoView({
      behavior: "smooth",
      block: "start",
    });
    if (restartTimer) setTimerKey((key) => key + 1);
  };

  useEffect(() => {
    remainingTime.current = SLIDE_DURATION_MS;
  }, [active, timerKey]);

  useEffect(() => {
    if (!dashboard || !autoplayEnabled || holdPaused || active >= 6) return;
    timerStartedAt.current = Date.now();
    const timer = window.setTimeout(() => {
      remainingTime.current = SLIDE_DURATION_MS;
      go(active + 1, false);
    }, remainingTime.current);
    return () => {
      window.clearTimeout(timer);
      remainingTime.current = Math.max(
        0,
        remainingTime.current - (Date.now() - timerStartedAt.current),
      );
    };
  }, [active, autoplayEnabled, dashboard, holdPaused, timerKey]);

  useEffect(() => {
    const release = () => setHoldPaused(false);
    window.addEventListener("pointerup", release);
    window.addEventListener("pointercancel", release);
    return () => {
      window.removeEventListener("pointerup", release);
      window.removeEventListener("pointercancel", release);
    };
  }, []);

  if (error)
    return (
      <section className="wrapped-state" role="alert">
        <h1>Wrapped is unavailable</h1>
        <p>{error}</p>
        <button onClick={() => window.location.reload()}>Try again</button>
      </section>
    );
  if (!dashboard || !forecast || !context)
    return (
      <section className="wrapped-state" role="status">
        <Sparkles />
        <h1>Building your financial story…</h1>
      </section>
    );

  const checking = accountTotal(dashboard, "checking");
  const savings = accountTotal(dashboard, "savings");
  const loans = accountTotal(dashboard, "loan");
  const cards = accountTotal(dashboard, "credit_card");
  const projectedEnding = forecast.series.at(-1)?.projected_balance;
  const low = forecast.projected_low;
  const score = Math.max(0, Math.min(100, dashboard.health_score));
  const healthTone = score >= 75 ? "strong" : score >= 50 ? "watch" : "risk";
  const categoryMax = Math.max(...topCategories.map((item) => item.amount), 1);
  const slideLabels = ["Snapshot", "Cash", "Debt", "Spending", "Health", "Economy", "Next move"];

  return (
    <div className="wrapped-shell">
      <div className="wrapped-autoplay" role="status" aria-live="polite">
        <button
          aria-label={active === 6 ? "Replay automatic slides" : !autoplayEnabled ? "Resume automatic slides" : "Switch to manual slides"}
          aria-pressed={!autoplayEnabled}
          onClick={() => {
            if (active === 6) {
              setAutoplayEnabled(true);
              go(0);
            } else {
              if (autoplayEnabled) {
                setAutoplayEnabled(false);
              } else {
                setAutoplayEnabled(true);
                setTimerKey((key) => key + 1);
              }
            }
          }}
        >
          {!autoplayEnabled || active === 6 ? <Play size={15} /> : <Pause size={15} />}
          <span>{active === 6 ? "Replay" : !autoplayEnabled ? "Resume timer" : "Manual mode"}</span>
        </button>
      </div>
      <div className="wrapped-progress" aria-label="Wrapped sections">
        {slideLabels.map((label, index) => (
          <button
            key={label}
            className={active === index ? "active" : ""}
            aria-label={`Go to ${label}`}
            aria-current={active === index ? "step" : undefined}
            onClick={() => go(index)}
          >
            <span />
          </button>
        ))}
      </div>
      {autoplayEnabled && active < 6 && (
        <div className="wrapped-timer-track" aria-label="Time remaining on this slide" role="progressbar">
          <div
            key={`${active}-${timerKey}`}
            className={`wrapped-timer ${holdPaused ? "held" : ""}`}
            style={{ "--slide-duration": `${SLIDE_DURATION_MS}ms` } as React.CSSProperties}
          />
        </div>
      )}
      <div
        className="wrapped-story"
        ref={story}
        tabIndex={0}
        onPointerDown={(event) => {
          if (event.button === 2 && autoplayEnabled) setHoldPaused(true);
        }}
        onContextMenu={(event) => event.preventDefault()}
      >
        <section className="wrapped-slide wrapped-hero" data-slide="0">
          <div className="wrapped-kicker"><Sparkles size={17} /> FINPILOT WRAPPED</div>
          <h1>Your FinPilot snapshot</h1>
          <p className="wrapped-lede">A seven-part view of where your finances stand and what deserves attention next.</p>
          <div className="wrapped-hero-value">
            <span>Net worth</span>
            <strong>{money(dashboard.net_worth)}</strong>
            <small>{money(dashboard.assets)} assets minus {money(dashboard.liabilities)} recorded debt</small>
          </div>
          <p className="wrapped-source">As of {context.as_of} · {context.data_source}</p>
          <button className="wrapped-next" onClick={() => go(1)}>Start the story <ArrowDown size={18} /></button>
        </section>

        <section className="wrapped-slide" data-slide="1">
          <div className="wrapped-kicker"><WalletCards size={17} /> 01 · CASH FOUNDATION</div>
          <h2>Your accessible cash</h2>
          <div className="wrapped-duo">
            <article><Landmark /><span>Checking</span><strong>{money(checking)}</strong><small>{dashboard.accounts.filter((a) => a.account_type === "checking").length} account(s)</small></article>
            <article><CircleDollarSign /><span>Savings</span><strong>{money(savings)}</strong><small>{dashboard.accounts.filter((a) => a.account_type === "savings").length} account(s)</small></article>
          </div>
          <p className="wrapped-insight">Together, these imported accounts hold <strong>{money(checking + savings)}</strong> before upcoming bills and spending.</p>
        </section>

        <section className="wrapped-slide" data-slide="2">
          <div className="wrapped-kicker"><Landmark size={17} /> 02 · DEBT PICTURE</div>
          <h2>What you currently owe</h2>
          <strong className="wrapped-big-number">{money(dashboard.liabilities)}</strong>
          <div className="wrapped-debt-grid">
            <div><span>Recorded loan principal</span><strong>{money(loans)}</strong></div>
            <div><span>Credit-card balances</span><strong>{money(cards)}</strong></div>
          </div>
          <p className="wrapped-insight">Debt balances affect net worth. Only dated payments appear in cash-flow projections.</p>
        </section>

        <section className="wrapped-slide" data-slide="3">
          <div className="wrapped-kicker"><ReceiptText size={17} /> 03 · LAST 30 DAYS</div>
          <h2>Top spending categories</h2>
          <strong className="wrapped-big-number">{money(dashboard.spending_30d)}</strong>
          <p className="wrapped-caption">Total classified cash spending</p>
          <div className="wrapped-categories">
            {topCategories.length ? topCategories.map((item) => (
              <div className="wrapped-category-row" key={item.category}>
                <div><span>{item.category.replace(/_/g, " ")}</span><strong>{money(item.amount)}</strong></div>
                <span className="wrapped-bar"><i style={{ width: `${(item.amount / categoryMax) * 100}%` }} /></span>
              </div>
            )) : <p>No classified spending was available for this period.</p>}
          </div>
          <p className="wrapped-insight">Imported inflows for the same period were <strong>{money(dashboard.income_30d)}</strong>. Deposits are not automatically treated as verified salary.</p>
        </section>

        <section className="wrapped-slide" data-slide="4">
          <div className="wrapped-kicker"><Activity size={17} /> 04 · FINANCIAL HEALTH</div>
          <h2>Your current estimate</h2>
          <div className="wrapped-score-layout">
            <div className={`wrapped-score ${healthTone}`} style={{ "--score": score } as React.CSSProperties}>
              <div><strong>{score.toFixed(1)}</strong><span>out of 100</span></div>
            </div>
            <div>
              <h3>{score >= 75 ? "A solid starting position" : score >= 50 ? "Some areas need attention" : "Your buffer needs attention"}</h3>
              <p>{dashboard.active_alerts[0]?.cause ?? "No configured Guardian rule is active in this snapshot."}</p>
            </div>
          </div>
          <p className="wrapped-insight">This is a prototype wellness estimate based on available records—not a credit score.</p>
        </section>

        <section className="wrapped-slide" data-slide="5">
          <div className="wrapped-kicker"><Globe2 size={17} /> 05 · ECONOMIC WEATHER</div>
          <h2>{economy?.status ?? "Economic context unavailable"}</h2>
          <div className="wrapped-economic-grid">
            <article><span>Pressure breadth</span><strong>{economy?.pressure_breadth_index == null ? "—" : `${economy.pressure_breadth_index.toFixed(0)}%`}</strong><small>Share of available dimensions with configured pressure signals</small></article>
            <article><span>Evidence coverage</span><strong>{economy?.evidence_quality ? `${economy.evidence_quality.available_dimensions}/${economy.evidence_quality.total_dimensions}` : "—"}</strong><small>Economic dimensions with usable data</small></article>
          </div>
          <div className="wrapped-advice"><ShieldCheck /><div><strong>How to react</strong><p>{economicGuidance(economy, dashboard)}</p></div></div>
          <p className="wrapped-caption">Descriptive conditions as of {economy?.as_of ?? context.as_of}; this is not a market-direction prediction.</p>
        </section>

        <section className="wrapped-slide wrapped-finale" data-slide="6">
          <div className="wrapped-kicker"><MessageSquareText size={17} /> 06 · YOUR NEXT MOVE</div>
          <h2>Turn the snapshot into a plan</h2>
          <div className="wrapped-outlook">
            <div><span>30-day projected ending checking</span><strong>{projectedEnding == null ? "Unavailable" : money(projectedEnding)}</strong></div>
            <div><span>Projected low</span><strong>{low ? money(low.balance) : "Unavailable"}</strong><small>{low?.date ?? ""}</small></div>
          </div>
          <p className="wrapped-lede">Ask FinPilot to explain an alert, compare a purchase, or test a change using verified backend calculations.</p>
          <div className="wrapped-actions">
            <button onClick={() => window.dispatchEvent(new Event("finpilot:open-chat"))}><MessageSquareText size={18} /> Ask FinPilot about my next move</button>
            <a href="#/digital-twin">Open Digital Twin</a>
          </div>
          <ReliabilityNotices
            groups={[dashboard.meta.notices ?? [], forecast.meta.notices ?? [], context.notices ?? []]}
            metas={[dashboard.meta, forecast.meta]}
          />
          <button className="wrapped-restart" onClick={() => go(0)}><ArrowUp size={16} /> Replay snapshot</button>
        </section>
      </div>
    </div>
  );
}
