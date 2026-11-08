// Pure helpers (no React, no DOM access at import time) so they can be unit-tested.
import type { Alert, Forecast, SpendingCut } from "./api";

export const money = (n: number) =>
  new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" }).format(n);
export const moneyShort = (n: number) => `${n < 0 ? "-" : ""}$${Math.abs(Math.round(n)).toLocaleString("en-US")}`;
const parseDay = (iso: string) => new Date(`${iso}T00:00:00Z`);
export const fmtDate = (iso: string) =>
  parseDay(iso).toLocaleDateString("en-US", { month: "short", day: "numeric", timeZone: "UTC" });
export const fmtDateLong = (iso: string) =>
  parseDay(iso).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric", timeZone: "UTC" });

/** `?debug` may sit in the hash (#/page?debug) or in the normal query string. */
export const isDebug = () =>
  typeof window !== "undefined" &&
  (new URLSearchParams(window.location.hash.split("?")[1] ?? "").has("debug") ||
    new URLSearchParams(window.location.search).has("debug"));
export const sourceLabel = (source: string) => (/nessie/i.test(source) ? "Bank sandbox data" : "Demo data");

export const methodLabel = (method?: string) =>
  ({
    moving_average_28: "your recent 28-day spending average",
    weekday_mean_90: "your typical spending for each weekday",
    rolling_average: "your recent spending average",
    lightgbm: "a spending model trained on sample data",
    baseline: "a simple baseline estimate",
  })[method ?? ""] ?? "your recent spending";

// Engineering wording from the backend is translated into plain language (raw text stays behind ?debug).
const plainRules: [RegExp, string][] = [
  [/moving_average|weekday_mean|variable-spending method/i, "Variable spending is estimated from your recent daily spending."],
  [/category vocabulary|PNC training/i, "Some spending categories may be estimated."],
  [/no applicable independent|serving baseline|not (been )?(independently )?validated/i, "This forecast has not been independently validated."],
  [/engineering-audit|synthetic prototype/i, "This prototype uses fictional demo data."],
];
export function plainAssumptions(lines: string[], debug = false): string[] {
  if (debug) return lines;
  const out: string[] = [];
  for (const line of lines) {
    const hit = plainRules.find(([re]) => re.test(line));
    const text = hit ? hit[1] : /\b[a-z]+_[a-z0-9_]+\b/.test(line) ? "" : line;
    if (text && !out.includes(text)) out.push(text);
  }
  return out;
}

export const describeCut = (c: SpendingCut) =>
  `Cut ${c.category ? `${c.category} ` : ""}spending by ${money(c.reduction_amount)} over the next ${c.horizon_days} days`;

export function alertFacts(a: Alert): string[] {
  const n = a.numbers ?? {};
  const v = (k: string) => (n[k] == null ? NaN : Number(n[k]));
  const out: string[] = [];
  if (typeof n.first_breach_date === "string")
    out.push(`Drops below your ${Number.isFinite(v("buffer")) ? `${money(v("buffer"))} ` : ""}buffer on ${fmtDate(n.first_breach_date)}`);
  if (Number.isFinite(v("projected_low")))
    out.push(`Lowest projected balance: ${money(v("projected_low"))}${typeof n.low_date === "string" ? ` on ${fmtDate(n.low_date)}` : ""}`);
  if (Number.isFinite(v("months_covered"))) out.push(`Savings cover ${v("months_covered").toFixed(1)} months of expenses (target: 3 months)`);
  if (Number.isFinite(v("debt_to_income"))) out.push(`Debt payments are ${(v("debt_to_income") * 100).toFixed(0)}% of income`);
  return out;
}

// Scheduled income and bills are recovered from the series itself (balance change + variable spending).
export type ForecastEvent = { date: string; amount: number; label: string };
export function forecastEvents(
  series: Forecast["series"],
  startBalance: number,
  bills: { name: string; amount: number; due_date: string }[],
): ForecastEvent[] {
  const out: ForecastEvent[] = [];
  let prev = startBalance;
  for (const r of series) {
    const scheduled = r.projected_balance - prev + r.predicted_spend;
    prev = r.projected_balance;
    if (Math.abs(scheduled) < 1) continue;
    let label = scheduled > 0 ? "Scheduled income" : "Scheduled payments";
    if (scheduled < 0) {
      const due = bills.filter((b) => b.due_date === r.date);
      if (due.length && Math.abs(due.reduce((s, b) => s + b.amount, 0) + scheduled) < 1) label = due.map((b) => b.name).join(" + ");
    }
    out.push({ date: r.date, amount: Math.round(scheduled * 100) / 100, label });
  }
  return out;
}
export const eventText = (e: ForecastEvent) => `${e.label} ${e.amount > 0 ? "+" : "−"}${money(Math.abs(e.amount))}`;
const truncate = (t: string, n: number) => (t.length > n ? `${t.slice(0, n - 1)}…` : t);
export const eventShort = (e: ForecastEvent) =>
  `${truncate(e.label.replace("Scheduled income", "Income").replace("Scheduled payments", "Payments"), 22)} ${e.amount > 0 ? "+" : "−"}${moneyShort(Math.abs(e.amount))}`;

export function niceTicks(min: number, max: number, count = 4): number[] {
  const span = Math.max(1, max - min);
  const raw = span / count, mag = 10 ** Math.floor(Math.log10(raw)), norm = raw / mag;
  const step = (norm <= 1 ? 1 : norm <= 2 ? 2 : norm <= 5 ? 5 : 10) * mag;
  const out: number[] = [];
  for (let v = Math.floor(min / step) * step; v <= Math.ceil(max / step) * step + 1e-9; v += step) out.push(Math.round(v * 100) / 100);
  if (out.length < 2) out.push(Math.round((out[0] + step) * 100) / 100); // flat data: always give the chart a range
  return out;
}
