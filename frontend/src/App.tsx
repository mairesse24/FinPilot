import { useEffect, useState } from "react";
import {
  Bell,
  ChevronDown,
  House,
  WalletCards,
  TrendingUp,
  BarChart3,
  ShieldCheck,
  Settings2,
  Globe2,
  MessageSquareText,
  Layers3,
  Menu,
  PanelLeftClose,
  PanelLeftOpen,
  X,
} from "lucide-react";
import ConnectedDashboard from "./ConnectedDashboard";
import EconomicIntelligence from "./EconomicIntelligence";
import FloatingCopilot from "./FloatingCopilot";
import { FinancialWorkspace } from "./FinancialWorkspace";
import { get, type Context, type Alert } from "./api";

const pages = [
  { label: "Overview", icon: House },
  { label: "My Finances", icon: WalletCards },
  { label: "Forecasts", icon: TrendingUp },
  { label: "Health Score", icon: BarChart3 },
  { label: "Guardian", icon: ShieldCheck },
  { label: "Digital Twin", icon: Settings2 },
  { label: "Economic Lab", icon: Globe2 },
  { label: "AI Co-Pilot", icon: MessageSquareText },
];
const route = (label: string) => "#/" + label.toLowerCase().replace(/ /g, "-");
const currentPage = () =>
  [...pages.map((p) => p.label), "FinPilot Wrapped"].find(
    (p) => route(p) === window.location.hash,
  ) ?? "Overview";

export default function App() {
  const [active, setActive] = useState(currentPage);
  const [collapsed, setCollapsed] = useState(false);
  const [mobile, setMobile] = useState(false);
  const [context, setContext] = useState<Context | null>(null);
  const [popover, setPopover] = useState<"profile" | "notifications" | null>(null);
  const [alerts, setAlerts] = useState<Alert[] | null>(null);
  const [error, setError] = useState("");
  useEffect(() => {
    const sync = () => {
      setActive(currentPage());
      setMobile(false);
      setPopover(null);
    };
    window.addEventListener("hashchange", sync);
    return () => window.removeEventListener("hashchange", sync);
  }, []);
  useEffect(() => {
    const c = new AbortController();
    get<Context>("context", c.signal)
      .then(setContext)
      .catch(() => {});
    return () => c.abort();
  }, []);
  useEffect(() => {
    const close = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        setPopover(null);
        setMobile(false);
      }
    };
    const outside = (e: MouseEvent) => {
      if (!(e.target as HTMLElement).closest(".header-controls")) setPopover(null);
    };
    document.addEventListener("keydown", close);
    document.addEventListener("click", outside);
    return () => {
      document.removeEventListener("keydown", close);
      document.removeEventListener("click", outside);
    };
  }, []);
  useEffect(() => {
    if (popover !== "notifications") return;
    const c = new AbortController();
    setAlerts(null);
    setError("");
    get<{ alerts: Alert[] }>("guardian", c.signal)
      .then((r) => {
        if (!c.signal.aborted) setAlerts(r.alerts);
      })
      .catch((e) => {
        if (!c.signal.aborted) setError(e.message);
      });
    return () => c.abort();
  }, [popover]);
  const name = context?.user.name || "Your profile";
  const initials = name
    .split(/\s+/)
    .slice(0, 2)
    .map((n) => n[0])
    .join("")
    .toUpperCase();
  return (
    <div className={`app-shell clean-shell ${collapsed ? "nav-collapsed" : ""}`}>
      {mobile && (
        <button
          className="sidebar-scrim"
          aria-label="Close navigation"
          onClick={() => setMobile(false)}
        />
      )}
      <aside
        className={`sidebar ${collapsed ? "sidebar-collapsed" : ""} ${mobile ? "sidebar-open" : ""}`}
      >
        <div className="sidebar-brand-row">
          <a className="wordmark" href="#/overview" aria-label="FinPilot home">
            F<span>inPilot</span>
          </a>
          <button
            className="mobile-close"
            aria-label="Close navigation"
            onClick={() => setMobile(false)}
          >
            <X size={18} />
          </button>
        </div>
        <nav className="sidebar-nav" aria-label="Primary navigation">
          {pages.map(({ label, icon: Icon }) => (
            <a
              key={label}
              href={route(label)}
              className={`nav-item ${active === label ? "active" : ""}`}
              aria-current={active === label ? "page" : undefined}
              title={label}
            >
              <Icon size={19} />
              <span>{label}</span>
            </a>
          ))}
        </nav>
        <div className="sidebar-footer">
          <p className="sandbox-label">Sandbox workspace</p>
          <button
            className="collapse-button"
            onClick={() => setCollapsed((v) => !v)}
            aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
          >
            {collapsed ? <PanelLeftOpen size={18} /> : <PanelLeftClose size={18} />}
            <span>Compact navigation</span>
          </button>
        </div>
      </aside>
      <a
        className="wrapped-floating"
        href="#/finpilot-wrapped"
        title="FinPilot Wrapped"
        aria-label="FinPilot Wrapped"
      >
        <Layers3 size={18} />
        <span>FinPilot Wrapped</span>
      </a>
      <main className="main-content">
        <header className="topbar">
          <button
            className="mobile-menu"
            aria-label="Open navigation"
            onClick={() => setMobile(true)}
          >
            <Menu size={20} />
          </button>
          <div className="workspace-label">
            Workspace <span>/ {active}</span>
          </div>
          <div className="header-controls">
            <button
              className="notification"
              aria-label="Notifications"
              aria-expanded={popover === "notifications"}
              onClick={() => setPopover((p) => (p === "notifications" ? null : "notifications"))}
            >
              <Bell size={20} />
            </button>
            <button
              className="profile"
              aria-label="Profile"
              aria-expanded={popover === "profile"}
              onClick={() => setPopover((p) => (p === "profile" ? null : "profile"))}
            >
              <span>{initials}</span>
              <div>
                <small>Personal workspace</small>
                <strong>{name}</strong>
              </div>
              <ChevronDown size={15} />
            </button>
            {popover === "profile" && (
              <section className="header-popover" aria-label="Profile details">
                <h2>{name}</h2>
                <p>{context?.data_source ?? "Profile is loading"}</p>
                <p>Financial snapshot: {context?.as_of ?? "Unavailable"}</p>
                <a href="#/my-finances" onClick={() => setPopover(null)}>
                  View my accounts
                </a>
                <p className="fine-print">
                  Synthetic banking data. No bank transactions can be executed here.
                </p>
              </section>
            )}
            {popover === "notifications" && (
              <section className="header-popover" aria-label="Current notifications">
                <h2>Financial alerts</h2>
                <p>Latest available analysis: {context?.as_of ?? ""}</p>
                {error ? (
                  <p role="alert">{error}</p>
                ) : !alerts ? (
                  <p role="status">Loading your alerts...</p>
                ) : alerts.length ? (
                  alerts.map((a) => (
                    <a className="notification-item" href="#/guardian" key={a.id}>
                      <span
                        className={`status-dot ${a.severity === "high" ? "tone-red" : a.severity === "medium" ? "tone-orange" : "tone-yellow"}`}
                      />
                      <div>
                        <strong>{a.title}</strong>
                        <small>{a.cause}</small>
                      </div>
                    </a>
                  ))
                ) : (
                  <p>No configured alerts are active. This does not guarantee financial safety.</p>
                )}
              </section>
            )}
          </div>
        </header>
        <FinancialWorkspace scope={context?.user.id}>
          <div className="dashboard">
            {["Economic Lab", "Health Score", "Digital Twin", "AI Co-Pilot"].includes(active) ? (
              <EconomicIntelligence page={active} />
            ) : (
              <ConnectedDashboard page={active} />
            )}
          </div>
          <FloatingCopilot />
        </FinancialWorkspace>
      </main>
    </div>
  );
}
