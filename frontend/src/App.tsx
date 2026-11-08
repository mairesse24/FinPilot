import { useEffect, useMemo, useState } from "react";
import {
  ArrowRight,
  BarChart3,
  Bell,
  CalendarDays,
  ChevronDown,
  ChevronRight,
  CircleDollarSign,
  CreditCard,
  EqualApproximately,
  Gauge,
  Globe2,
  House,
  Info,
  Landmark,
  Layers3,
  Menu,
  MessageSquareText,
  PanelLeftClose,
  PanelLeftOpen,
  ReceiptText,
  Route,
  Settings2,
  ShieldCheck,
  Sparkles,
  TrendingDown,
  TrendingUp,
  WalletCards,
  X,
  type LucideIcon,
} from "lucide-react";

type Period = "7D" | "30D" | "90D";
type NavItem = {
  label: string;
  icon: LucideIcon;
};

const navItems: NavItem[] = [
  { label: "Overview", icon: House },
  { label: "My Finances", icon: WalletCards },
  { label: "Forecasts", icon: TrendingUp },
  { label: "Health Score", icon: BarChart3 },
  { label: "Guardian", icon: ShieldCheck },
  { label: "Digital Twin", icon: Settings2 },
  { label: "Economic Lab", icon: Globe2 },
  { label: "AI Co-Pilot", icon: MessageSquareText },
  { label: "FinPilot Wrapped", icon: Layers3 },
];

const routeFor = (label: string) => label.toLowerCase().replace(/ /g, "-");
const pageFromHash = () => navItems.find(item => '#/' + routeFor(item.label) === window.location.hash)?.label ?? "Overview";
const scoreBreakdown = [
  { label: "Cash Flow Stability", value: 92, icon: TrendingUp },
  { label: "Savings Readiness", value: 86, icon: Landmark },
  { label: "Debt Management", value: 82, icon: CreditCard },
  { label: "Spending Discipline", value: 85, icon: Settings2 },
  { label: "Payment Readiness", value: 88, icon: ReceiptText },
];

const alerts = [
  {
    title: "Upcoming Bill",
    detail: "$1,200 rent due in 5 days",
    level: "HIGH",
    tone: "high",
    icon: ReceiptText,
  },
  {
    title: "Low Balance Risk",
    detail: "Projected: $2,480 in 30 days",
    level: "MEDIUM",
    tone: "medium",
    icon: CircleDollarSign,
  },
  {
    title: "Unusual Spending",
    detail: "+22% vs. your average",
    level: "MEDIUM",
    tone: "medium",
    icon: TrendingUp,
  },
  {
    title: "Interest Rate Impact",
    detail: "May increase monthly payments",
    level: "LOW",
    tone: "low",
    icon: EqualApproximately,
  },
];

const periodData: Record<
  Period,
  { projected: string; change: string; confidence: string; path: string }
> = {
  "7D": {
    projected: "$5,180",
    change: "-4.1%",
    confidence: "92%",
    path: "M0 96 C65 84 92 112 150 87 S245 72 300 78 S405 48 480 53 S610 42 730 19",
  },
  "30D": {
    projected: "$6,140",
    change: "+13.7%",
    confidence: "86%",
    path: "M0 73 C48 57 85 104 143 77 S238 108 297 91 S370 52 434 68 S520 48 585 46 S650 23 730 25",
  },
  "90D": {
    projected: "$8,920",
    change: "+65.2%",
    confidence: "78%",
    path: "M0 65 C52 58 70 96 127 72 S211 87 261 88 S347 56 399 65 S472 50 521 47 S600 17 652 23 S699 11 730 7",
  },
};

function Logo() {
  return (
    <div className="brand">
      <div className="brand-mark" aria-hidden="true">
        <span />
        <span />
      </div>
      <div>
        <div className="brand-name">
          Fin<span>Pilot</span>
        </div>
        <div className="brand-tagline">See deeper. Act smarter.</div>
      </div>
    </div>
  );
}

function Sidebar({
  active,
  setActive,
  open,
  close,
  collapsed,
  toggleCollapsed,
}: {
  active: string;
  setActive: (item: string) => void;
  open: boolean;
  close: () => void;
  collapsed: boolean;
  toggleCollapsed: () => void;
}) {
  return (
    <>
      {open && <button className="sidebar-scrim" onClick={close} aria-label="Close navigation" />}
      <aside
        className={`sidebar ${open ? "sidebar-open" : ""} ${collapsed ? "sidebar-collapsed" : ""}`}
      >
        <div className="sidebar-brand-row">
          <Logo />
          <button className="mobile-close" onClick={close} aria-label="Close navigation">
            <X size={20} />
          </button>
        </div>

        <nav className="sidebar-nav" aria-label="Primary navigation">
          {navItems.map(({ label, icon: Icon }) => (
            <a
              href={"#/" + routeFor(label)}
              aria-current={active === label ? "page" : undefined}
              key={label}
              title={collapsed ? label : undefined}
              className={`nav-item ${active === label ? "active" : ""}`}
              onClick={() => {
                setActive(label);
                close();
              }}
            >
              <Icon size={20} strokeWidth={1.9} />
              <span>{label}</span>
              {label === "Guardian" && <i>4</i>}
            </a>
          ))}
        </nav>

        <div className="sidebar-footer">
          <div className="system-status">
            <span />
            <div>
              <strong>All systems nominal</strong>
              <small>Last synced 2 min ago</small>
            </div>
          </div>
          <button className="collapse-button" onClick={toggleCollapsed}>
            {collapsed ? <PanelLeftOpen size={18} /> : <PanelLeftClose size={18} />}
            <span>Collapse sidebar</span>
          </button>
        </div>
      </aside>
    </>
  );
}

function MetricCard({
  icon: Icon,
  label,
  value,
  change,
  negative = false,
}: {
  icon: LucideIcon;
  label: string;
  value: string;
  change?: string;
  negative?: boolean;
}) {
  return (
    <article className="metric-card">
      <div className="metric-icon">
        <Icon size={20} />
      </div>
      <div className="metric-copy">
        <span>{label}</span>
        <strong>{value}</strong>
      </div>
      {change && (
        <div className={`metric-change ${negative ? "negative" : ""}`}>
          <span>
            {negative ? "▼" : "▲"} {change}
          </span>
          <small>MoM</small>
        </div>
      )}
    </article>
  );
}

function HealthScore() {
  return (
    <article className="panel health-panel">
      <div className="score-ring">
        <svg viewBox="0 0 220 220" aria-hidden="true">
          <defs>
            <linearGradient id="scoreGradient" x1="0" y1="0" x2="1" y2="1">
              <stop offset="0" stopColor="#00e5c3" />
              <stop offset=".7" stopColor="#00e5c3" />
              <stop offset="1" stopColor="#263847" />
            </linearGradient>
          </defs>
          <circle className="score-track" cx="110" cy="110" r="91" />
          <circle className="score-progress" cx="110" cy="110" r="91" />
        </svg>
        <div className="score-content">
          <span>
            Financial
            <br />
            health score
          </span>
          <strong>87</strong>
          <small>/100</small>
        </div>
      </div>
      <div className="score-badge">Excellent</div>
    </article>
  );
}

function ScoreBreakdown() {
  return (
    <article className="panel score-panel">
      <div className="panel-title">
        <h2>Score Breakdown</h2>
        <Info size={17} />
      </div>
      <div className="score-list">
        {scoreBreakdown.map(({ label, value, icon: Icon }) => (
          <div className="score-row" key={label}>
            <Icon size={18} />
            <div className="score-metric">
              <div>
                <span>{label}</span>
                <strong>{value}%</strong>
              </div>
              <div className="progress-track">
                <span style={{ width: `${value}%` }} />
              </div>
            </div>
          </div>
        ))}
      </div>
    </article>
  );
}

function GuardianPanel({ onSimulate }: { onSimulate: () => void }) {
  const [selected, setSelected] = useState(0);
  const activeAlert = alerts[selected];
  return (
    <article className="panel guardian-panel">
      <button
        className="panel-title guardian-title"
        onClick={() => setSelected((selected + 1) % alerts.length)}
      >
        <span className="title-icon">
          <ShieldCheck size={21} />
        </span>
        <span>
          <h2>FinPilot Guardian</h2>
          <small>4 active alerts</small>
        </span>
        <ChevronRight size={20} />
      </button>
      <div className="alert-list">
        {alerts.map(({ title, detail, level, tone, icon: Icon }, index) => (
          <button
            className={`alert-row ${tone} ${selected === index ? "selected" : ""}`}
            key={title}
            onClick={() => setSelected(index)}
          >
            <Icon size={19} />
            <span>
              <strong>{title}</strong>
              <small>{detail}</small>
            </span>
            <em>{level}</em>
          </button>
        ))}
      </div>
      <div className={`guardian-detail ${activeAlert.tone}`}>
        <span>Recommended next step</span>
        <strong>
          {selected === 0
            ? "Test a $200 spending reduction"
            : "Review this risk in your Digital Twin"}
        </strong>
        <button onClick={onSimulate}>
          Simulate <ArrowRight size={14} />
        </button>
      </div>
    </article>
  );
}

function ForecastChart({
  period,
  setPeriod,
}: {
  period: Period;
  setPeriod: (period: Period) => void;
}) {
  const data = periodData[period];
  return (
    <article className="panel forecast-panel">
      <div className="chart-header">
        <div className="panel-title">
          <span className="title-icon">
            <TrendingUp size={20} />
          </span>
          <div>
            <h2>Cash Flow Forecast</h2>
            <small>Projected available balance</small>
          </div>
        </div>
        <div className="period-switch" role="group" aria-label="Forecast range">
          {(Object.keys(periodData) as Period[]).map((item) => (
            <button
              className={period === item ? "active" : ""}
              onClick={() => setPeriod(item)}
              key={item}
            >
              {item}
            </button>
          ))}
        </div>
      </div>

      <div className="chart-area">
        <div className="y-labels">
          <span>$10K</span>
          <span>$8K</span>
          <span>$6K</span>
          <span>$4K</span>
          <span>$2K</span>
          <span>$0</span>
        </div>
        <div className="chart-canvas">
          <div className="projected-low">
            <TrendingDown size={15} />
            <span>
              Projected low: <strong>$2,480</strong>
            </span>
          </div>
          <svg
            preserveAspectRatio="none"
            viewBox="0 0 730 120"
            aria-label={`${period} projected cash flow`}
          >
            <defs>
              <linearGradient id="areaGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0" stopColor="#00e5c3" stopOpacity=".36" />
                <stop offset="1" stopColor="#00e5c3" stopOpacity="0" />
              </linearGradient>
              <filter id="lineGlow">
                <feGaussianBlur stdDeviation="3" result="blur" />
                <feMerge>
                  <feMergeNode in="blur" />
                  <feMergeNode in="SourceGraphic" />
                </feMerge>
              </filter>
            </defs>
            <path d={`${data.path} L730 120 L0 120 Z`} fill="url(#areaGradient)" />
            <path
              d={data.path}
              fill="none"
              stroke="#00e5c3"
              strokeWidth="3"
              filter="url(#lineGlow)"
            />
            <line
              x1="265"
              y1="0"
              x2="265"
              y2="120"
              stroke="#f59e0b"
              strokeDasharray="4 4"
              opacity=".75"
            />
            <circle cx="265" cy="88" r="6" fill="#f59e0b" stroke="#fff1ce" strokeWidth="2" />
          </svg>
          <div className="x-labels">
            <span>Now</span>
            <span>15D</span>
            <span>30D</span>
            <span>45D</span>
            <span>60D</span>
            <span>75D</span>
            <span>90D</span>
          </div>
        </div>
      </div>
      <div className="forecast-disclaimer">
        <Info size={13} />
        Prototype estimate based on simulated financial data
      </div>
    </article>
  );
}

function ForecastSummary({ period, onSimulate }: { period: Period; onSimulate: () => void }) {
  const data = periodData[period];
  return (
    <article className="panel summary-panel">
      <div className="panel-title">
        <span className="title-icon">
          <CalendarDays size={19} />
        </span>
        <h2>Forecast Summary</h2>
      </div>
      <div className="summary-rows">
        <div>
          <span>Projected balance ({period})</span>
          <strong>{data.projected}</strong>
        </div>
        <div>
          <span>Change from today</span>
          <strong className={data.change.startsWith("-") ? "rose" : "green"}>{data.change}</strong>
        </div>
        <div>
          <span>Confidence level</span>
          <strong>{data.confidence}</strong>
        </div>
      </div>
      <button className="primary-button" onClick={onSimulate}>
        <Settings2 size={18} />
        Re-route in Digital Twin
        <ArrowRight size={18} />
      </button>
    </article>
  );
}

function QuickAction({
  icon: Icon,
  title,
  text,
  tone,
  onClick,
}: {
  icon: LucideIcon;
  title: string;
  text: string;
  tone: string;
  onClick: () => void;
}) {
  return (
    <button className={`quick-action ${tone}`} onClick={onClick}>
      <Icon size={29} />
      <span>
        <strong>{title}</strong>
        <small>{text}</small>
      </span>
      <ChevronRight size={18} />
    </button>
  );
}

function SimulatorDrawer({ close }: { close: () => void }) {
  const [reduction, setReduction] = useState(200);
  const outcome = useMemo(() => 320 + reduction, [reduction]);
  return (
    <div className="drawer-scrim" onClick={close}>
      <aside className="simulator-drawer" onClick={(event) => event.stopPropagation()}>
        <div className="drawer-header">
          <div>
            <span className="eyebrow">Financial Digital Twin</span>
            <h2>Re-route your forecast</h2>
          </div>
          <button onClick={close} aria-label="Close simulator">
            <X size={20} />
          </button>
        </div>
        <div className="scenario-card">
          <Route size={23} />
          <div>
            <strong>Reduce discretionary spending</strong>
            <span>See how a monthly adjustment changes your projected low.</span>
          </div>
        </div>
        <label className="slider-label">
          Monthly reduction
          <strong>${reduction}</strong>
        </label>
        <input
          type="range"
          min="0"
          max="500"
          step="25"
          value={reduction}
          onChange={(event) => setReduction(Number(event.target.value))}
        />
        <div className="comparison">
          <div>
            <span>Current path</span>
            <strong>$320</strong>
            <small>Projected low</small>
          </div>
          <ArrowRight size={20} />
          <div className="improved">
            <span>New path</span>
            <strong>${outcome}</strong>
            <small>{outcome >= 500 ? "Above safety buffer" : "Below safety buffer"}</small>
          </div>
        </div>
        <div className="copilot-note">
          <Sparkles size={18} />
          <p>
            This change could lift your projected low by <strong>${reduction}</strong>.
            {outcome >= 500
              ? " You would clear your $500 safety buffer, with some uncertainty remaining."
              : " Try increasing the adjustment to reach your $500 safety buffer."}
          </p>
        </div>
        <button className="primary-button wide" onClick={close}>
          Done exploring scenario
        </button>
        <p className="fine-print">Illustrative simulation only. No account changes will be made.</p>
      </aside>
    </div>
  );
}

function CopilotDrawer({ close }: { close: () => void }) {
  const [message, setMessage] = useState("");
  const [sent, setSent] = useState(false);
  return (
    <div className="drawer-scrim" onClick={close}>
      <aside
        className="simulator-drawer copilot-drawer"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="drawer-header">
          <div>
            <span className="eyebrow">Calculation-grounded guidance</span>
            <h2>Ask FinPilot AI</h2>
          </div>
          <button onClick={close} aria-label="Close co-pilot">
            <X size={20} />
          </button>
        </div>
        <div className="chat-bubble assistant">
          <Sparkles size={17} />
          <p>
            Your Guardian found one high-priority alert: rent is due before your next paycheck. I
            can explain the forecast or compare safer scenarios.
          </p>
        </div>
        {sent && (
          <>
            <div className="chat-bubble user">
              <p>{message || "How can I improve my projected balance?"}</p>
            </div>
            <div className="chat-bubble assistant">
              <Sparkles size={17} />
              <p>
                In this illustrative scenario, reducing discretionary spending by $200 raises your
                projected low from $320 to $520, just above your safety buffer.
              </p>
            </div>
          </>
        )}
        <div className="prompt-chips">
          <button onClick={() => setMessage("Explain my biggest risk")}>
            Explain my biggest risk
          </button>
          <button onClick={() => setMessage("How was my score calculated?")}>
            How was my score calculated?
          </button>
        </div>
        <form
          className="chat-input"
          onSubmit={(event) => {
            event.preventDefault();
            setSent(true);
          }}
        >
          <input
            value={message}
            onChange={(event) => setMessage(event.target.value)}
            placeholder="Ask about your financial outlook..."
          />
          <button aria-label="Send message">
            <ArrowRight size={18} />
          </button>
        </form>
        <p className="fine-print">Demo explanations use simulated data and scripted responses.</p>
      </aside>
    </div>
  );
}

function SectionPage({ active, period, setPeriod, navigate, simulate, chat }: {
 active: string; period: Period; setPeriod: (value: Period) => void;
 navigate: (page: string) => void; simulate: () => void; chat: () => void;
}) {
 const [rate, setRate] = useState(2);
 const [filter, setFilter] = useState("All");
 return <>
 <section className="welcome"><div><span className="eyebrow">FinPilot / {active}</span><h1>{active}</h1><p>Your financial freedom mission, one step at a time.</p></div><a className="primary-button" href="#/overview">Back to overview <ArrowRight size={16} /></a></section>
 <p className="demo-label">Demo workspace ? All balances and projections use simulated data.</p>
 {active === "My Finances" && <><section className="section-metrics"><MetricCard icon={Layers3} label="Net Worth" value="$24,850" /><MetricCard icon={WalletCards} label="Available Cash" value="$5,400" /><MetricCard icon={TrendingUp} label="Monthly Income" value="$4,300" /><MetricCard icon={ReceiptText} label="Monthly Expenses" value="$2,150" /></section><section className="section-grid"><article className="panel detail-panel"><h2>Monthly budget</h2>{[["Income", "$4,300"], ["Expenses", "$2,150"], ["Remaining", "$2,150"]].map(([label, value]) => <div className="detail-row" key={label}><span>{label}</span><strong>{value}</strong></div>)}<button className="primary-button" onClick={() => navigate("Forecasts")}>View cash flow <ArrowRight size={16} /></button></article><article className="panel detail-panel"><h2>Upcoming obligation</h2><div className="scenario-card"><ReceiptText /><div><strong>Rent ? $1,200</strong><span>Due in 5 days</span></div></div><button className="primary-button" onClick={() => navigate("Guardian")}>Review bill alert</button></article></section></>}
 {active === "Forecasts" && <section className="forecast-grid"><ForecastChart period={period} setPeriod={setPeriod} /><ForecastSummary period={period} onSimulate={simulate} /></section>}
 {active === "Health Score" && <section className="section-grid"><HealthScore /><ScoreBreakdown /><article className="panel detail-panel"><h2>Build on your progress</h2><p>Debt management is your lowest scoring factor at 82%. Explore your spending and test adjustments to your plan.</p><button className="primary-button" onClick={() => navigate("Digital Twin")}>Test an adjustment</button></article></section>}
 {active === "Guardian" && <><div className="period-switch section-filter" role="group" aria-label="Filter alerts">{["All", "HIGH", "MEDIUM", "LOW"].map(level => <button key={level} aria-pressed={filter === level} className={filter === level ? "active" : ""} onClick={() => setFilter(level)}>{level}</button>)}</div><section className="section-grid">{alerts.filter(alert => filter === "All" || alert.level === filter).map(({ title, detail, level, icon: Icon }) => <article className="panel detail-panel" key={title}><div className="panel-title"><Icon size={22} /><h2>{title}</h2></div><span className="eyebrow">{level} priority</span><p>{detail}</p><button className="primary-button" onClick={simulate}>Explore a scenario <ArrowRight size={16} /></button></article>)}</section></>}
 {active === "Digital Twin" && <section className="section-grid"><article className="panel detail-panel"><div className="panel-title"><Route /><h2>Your financial sandbox</h2></div><p>Adjust monthly discretionary spending and compare the sample projected low against a $500 safety buffer.</p><button className="primary-button" onClick={simulate}>Launch simulator</button></article><article className="panel detail-panel"><h2>Compare your outlook</h2><p>Explore the 7, 30, and 90 day projections.</p><button className="primary-button" onClick={() => navigate("Forecasts")}>Open forecasts</button></article></section>}
 {active === "Economic Lab" && <section className="section-grid"><article className="panel detail-panel"><div className="panel-title"><Globe2 /><h2>Cost increase scenario</h2></div><p>Apply an illustrative increase to your $2,150 monthly expenses. This is a simple sensitivity calculation.</p><label className="slider-label" htmlFor="cost-increase">Expense increase <strong>{rate}%</strong></label><input id="cost-increase" type="range" min="0" max="10" step="0.5" value={rate} onChange={event => setRate(Number(event.target.value))} /><div className="detail-row"><span>Additional monthly cost</span><strong>$ {(2150 * rate / 100).toFixed(2)}</strong></div><div className="detail-row"><span>Adjusted monthly expenses</span><strong>$ {(2150 * (1 + rate / 100)).toFixed(2)}</strong></div><button className="primary-button" onClick={simulate}>Explore a spending adjustment</button></article></section>}
 {active === "AI Co-Pilot" && <section className="section-grid"><article className="panel detail-panel"><div className="panel-title"><Sparkles /><h2>Plan your next step</h2></div><p>Review the upcoming rent alert or explore a sample spending scenario.</p><button className="primary-button" onClick={chat}>Open demo conversation <MessageSquareText size={16} /></button><p className="fine-print">Scripted prototype responses. A live AI service is not connected.</p></article><article className="panel detail-panel"><h2>Explore your data</h2><p>Review the factors behind your outlook.</p><button className="primary-button" onClick={() => navigate("Health Score")}>See health factors</button><button className="text-link" onClick={() => navigate("Guardian")}>Review Guardian alerts</button></article></section>}
 {active === "FinPilot Wrapped" && <><section className="section-metrics"><MetricCard icon={BarChart3} label="Health Score" value="87 / 100" /><MetricCard icon={Layers3} label="Net Worth Growth" value="+5.2%" /><MetricCard icon={WalletCards} label="Cash Growth" value="+3.8%" /><MetricCard icon={TrendingUp} label="Monthly Surplus" value="$2,150" /></section><article className="panel detail-panel"><span className="eyebrow">Your monthly snapshot</span><h2>A stronger financial foundation</h2><p>Cash flow stability leads your health factors at 92%. Your next planning opportunity: review the rent obligation and compare spending scenarios.</p><button className="primary-button" onClick={() => navigate("Guardian")}>Plan next month</button></article></>}
 </>;
}

export default function App() {
  const [active, updateActive] = useState(pageFromHash);
  const setActive = (label: string) => { window.location.hash = '/' + routeFor(label); updateActive(label); };
  useEffect(() => {
    const sync = () => { updateActive(pageFromHash()); setMobileNav(false); setDrawer(null); window.scrollTo(0, 0); };
    window.addEventListener("hashchange", sync);
    return () => window.removeEventListener("hashchange", sync);
  }, []);
  const [period, setPeriod] = useState<Period>("90D");
  const [mobileNav, setMobileNav] = useState(false);
  const [collapsed, setCollapsed] = useState(false);
  const [drawer, setDrawer] = useState<"simulator" | "copilot" | null>(null);

  return (
    <div className={`app-shell ${collapsed ? "nav-collapsed" : ""}`}>
      <Sidebar
        active={active}
        setActive={setActive}
        open={mobileNav}
        close={() => setMobileNav(false)}
        collapsed={collapsed}
        toggleCollapsed={() => setCollapsed(!collapsed)}
      />

      <main className="main-content">
        <header className="topbar">
          <button
            className="mobile-menu"
            onClick={() => setMobileNav(true)}
            aria-label="Open navigation"
          >
            <Menu size={21} />
          </button>
          <div className="mission">
            <strong>
              Mission: <span>Financial freedom</span>
            </strong>
            <small>A 360° financial health navigator</small>
          </div>
          <div className="topbar-actions">
            <div className="date">
              <CalendarDays size={18} />
              <span>Nov 7, 2026</span>
            </div>
            <button className="icon-button notification" aria-label="Notifications" onClick={() => setActive("Guardian")}>
              <Bell size={19} />
              <i />
            </button>
            <button className="profile" onClick={() => setActive("My Finances")}>
              <span>MP</span>
              <div>
                <small>Welcome back</small>
                <strong>Mairesse</strong>
              </div>
              <ChevronDown size={15} />
            </button>
          </div>
        </header>

        <div className="dashboard">
{active === "Overview" ? <>
          <section className="welcome">
            <div>
              <span className="eyebrow">Saturday, November 7</span>
              <h1>Good afternoon, Mairesse</h1>
              <p>
                Your finances are on track. One upcoming obligation could affect your cash flow —
                let’s plan ahead.
              </p>
            </div>
            <div className="secure-badge">
              <ShieldCheck size={15} /> Protected with synthetic data
            </div>
          </section>

          <section className="overview-grid">
            <div className="metrics-stack">
              <MetricCard icon={Layers3} label="Net Worth" value="$24,850" change="+5.2%" />
              <MetricCard icon={WalletCards} label="Available Cash" value="$5,400" change="+3.8%" />
              <MetricCard icon={TrendingUp} label="Monthly Income" value="$4,300" />
              <MetricCard
                icon={ReceiptText}
                label="Monthly Expenses"
                value="$2,150"
                change="+4.1%"
                negative
              />
            </div>
            <HealthScore />
            <ScoreBreakdown />
            <GuardianPanel onSimulate={() => setDrawer("simulator")} />
          </section>

          <section className="forecast-grid">
            <ForecastChart period={period} setPeriod={setPeriod} />
            <ForecastSummary period={period} onSimulate={() => setDrawer("simulator")} />
          </section>

          <section className="quick-grid">
            <QuickAction
              icon={Settings2}
              title="Explore a Scenario"
              text="Test decisions before they affect your finances."
              tone="teal"
              onClick={() => setDrawer("simulator")}
            />
            <QuickAction
              icon={MessageSquareText}
              title="Ask FinPilot AI"
              text="Get grounded insights and clear next steps."
              tone="violet"
              onClick={() => setDrawer("copilot")}
            />
            <QuickAction
              icon={Globe2}
              title="Economic Lab"
              text="Understand how the economy may affect you."
              tone="cyan"
              onClick={() => setActive("Economic Lab")}
            />
            <QuickAction
              icon={Layers3}
              title="FinPilot Wrapped"
              text="Your financial journey, insights, and outlook."
              tone="amber"
              onClick={() => setActive("FinPilot Wrapped")}
            />
          </section>
</> : <SectionPage key={active} active={active} period={period} setPeriod={setPeriod} navigate={setActive} simulate={() => setDrawer("simulator")} chat={() => setDrawer("copilot")} />}
        </div>
      </main>

      {drawer === "simulator" && <SimulatorDrawer close={() => setDrawer(null)} />}
      {drawer === "copilot" && <CopilotDrawer close={() => setDrawer(null)} />}
    </div>
  );
}
