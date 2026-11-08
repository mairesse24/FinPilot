export type Notice = {
  code: string;
  context: string;
  category: "critical" | "data_limitation" | "diagnostic";
  message: string;
  technical_detail: string;
};
export type Meta = {
  source: string;
  as_of: string;
  warning: string | null;
  notices?: Notice[];
  forecast_reliability?: {
    method: string;
    status: string;
    validation: string;
    reasons: string[];
  } | null;
};
export type SpendingCut = {
  type: "spending_cut";
  reduction_amount: number;
  horizon_days: number;
  category?: string | null;
};
export type Alert = {
  id: string;
  rule?: string;
  title: string;
  severity: string;
  cause: string;
  recommended_action: string;
  numbers?: Record<string, number | string>;
  suggested_scenario?: SpendingCut | null;
};
export type ScenarioOutcome = {
  projected_low: { date: string; balance: number } | null;
  end_balance: number;
  health_score: number;
  alerts: Alert[];
};
export type SimulationResult = {
  baseline: ScenarioOutcome;
  scenario: ScenarioOutcome;
  delta: Record<string, number>;
  meta: Meta;
};
export type HealthComponent = {
  key: string;
  name: string;
  weight: number;
  score: number;
  explanation: string;
};
export type HealthV1 = {
  score: number;
  components: HealthComponent[];
  strengths: string[];
  weaknesses: string[];
  meta: Meta;
};
export type Account = {
  id: string;
  name: string;
  account_type: string;
  balance: number;
  apr?: number | null;
  min_payment?: number | null;
  credit_limit?: number | null;
};
export type Dashboard = {
  net_worth: number;
  assets: number;
  liabilities: number;
  income_30d: number;
  spending_30d: number;
  accounts: Account[];
  by_category: { category: string; amount: number }[];
  upcoming_bills: { name: string; amount: number; due_date: string }[];
  health_score: number;
  active_alerts: Alert[];
  meta: Meta;
};
export type Forecast = {
  status?: "estimated" | "limited_history" | "abstained";
  days: number;
  safety_buffer: number;
  shortfall: boolean;
  series: {
    date: string;
    projected_balance: number;
    low: number;
    high: number;
    predicted_spend: number;
  }[];
  projected_low: { date: string; balance: number } | null;
  assumptions: string[];
  meta: Meta;
};
export type Context = {
  user: { id: string; name: string };
  as_of: string;
  data_source: string;
  warnings: string[];
  notices?: Notice[];
  loaded_at: string | null;
};

// Empty in local dev (Vite proxies /api to the backend). Set VITE_API_BASE at build time
// (for example https://finpilot-xxxx.onrender.com) when the frontend is hosted separately.
export const API_BASE: string = ((import.meta as unknown as { env?: Record<string, string | undefined> }).env?.VITE_API_BASE ?? '').replace(/\/+$/, '');

export async function get<T>(path: string, signal: AbortSignal): Promise<T> {
  const response = await fetch(`${API_BASE}/api/${path}`, { signal, cache: "no-store" });
  if (!response.ok)
    throw new Error(
      `API ${response.status}: unable to load ${path.split("?")[0]}. Check backend configuration.`,
    );
  if (!response.headers.get("content-type")?.includes("application/json"))
    throw new Error("API unavailable. Start the backend on port 8000.");
  return response.json() as Promise<T>;
}

export async function post<T>(path: string, body?: object): Promise<T> {
  const response = await fetch(`${API_BASE}/api/${path}`, {
    method: "POST",
    cache: "no-store",
    headers: { "Content-Type": "application/json" },
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw new Error(typeof payload.detail === "string" ? payload.detail : "The simulation could not run.");
  }
  return response.json() as Promise<T>;
}
