// Shared, module-level cache for the dashboard data. Pages read from here, so moving between
// routes never refetches (and never shows the loading state again). Reload clears it.
import { useEffect, useSyncExternalStore, useState } from "react";
import { get, type Context, type Dashboard, type Forecast, type HealthV1 } from "./api";

type Phase = "idle" | "loading" | "ready" | "error";
type Slice<T> = { phase: Phase; data: T | null; error: string; startedAt: number };
type Core = { dashboard: Dashboard; context: Context };
type State = {
  core: Slice<Core>;
  forecasts: Record<number, Slice<Forecast>>;
  health: Slice<HealthV1>;
};

const blank = <T,>(): Slice<T> => ({ phase: "idle", data: null, error: "", startedAt: 0 });
let state: State = { core: blank(), forecasts: {}, health: blank() };
// Every reload starts a new epoch; answers that belong to an older epoch are ignored, so a slow
// response (or a late failure) from before a reload can never overwrite fresher data.
let epoch = 0;
const listeners = new Set<() => void>();
const update = (fn: (s: State) => State) => {
  state = fn(state);
  listeners.forEach((l) => l());
};
const never = new AbortController().signal;
const current = (mine: number) => mine === epoch;

export function loadCore(force = false) {
  if (!force && state.core.phase !== "idle") return;
  const mine = epoch;
  update((s) => ({ ...s, core: { phase: "loading", data: null, error: "", startedAt: Date.now() } }));
  Promise.all([get<Dashboard>("dashboard", never), get<Context>("context", never)])
    .then(([dashboard, context]) => {
      if (current(mine)) update((s) => ({ ...s, core: { phase: "ready", data: { dashboard, context }, error: "", startedAt: 0 } }));
    })
    .catch((e) => {
      if (current(mine)) update((s) => ({ ...s, core: { phase: "error", data: null, error: String(e.message), startedAt: 0 } }));
    });
}

export function loadForecast(days: number, force = false) {
  if (!force && state.forecasts[days]) return;
  const mine = epoch;
  update((s) => ({
    ...s,
    forecasts: { ...s.forecasts, [days]: { phase: "loading", data: null, error: "", startedAt: Date.now() } },
  }));
  get<Forecast>(`forecast?days=${days}`, never)
    .then((f) => {
      if (current(mine)) update((s) => ({ ...s, forecasts: { ...s.forecasts, [days]: { phase: "ready", data: f, error: "", startedAt: 0 } } }));
    })
    .catch((e) => {
      if (current(mine))
        update((s) => ({
          ...s,
          forecasts: { ...s.forecasts, [days]: { phase: "error", data: null, error: String(e.message), startedAt: 0 } },
        }));
    });
}

export function loadHealth(force = false) {
  if (!force && state.health.phase !== "idle") return;
  const mine = epoch;
  update((s) => ({ ...s, health: { phase: "loading", data: null, error: "", startedAt: Date.now() } }));
  get<HealthV1>("health", never)
    .then((h) => {
      if (current(mine)) update((s) => ({ ...s, health: { phase: "ready", data: h, error: "", startedAt: 0 } }));
    })
    .catch((e) => {
      if (current(mine)) update((s) => ({ ...s, health: { phase: "error", data: null, error: String(e.message), startedAt: 0 } }));
    });
}

export function reloadAll(days: number) {
  epoch += 1;
  update(() => ({ core: blank(), forecasts: {}, health: blank() }));
  loadCore(true);
  loadForecast(days, true);
  loadHealth(true);
}

const subscribe = (l: () => void) => {
  listeners.add(l);
  return () => listeners.delete(l);
};

/** True once a request has been pending longer than `afterMs` (free hosting can take a minute to wake). */
export function useSlow(pending: boolean, afterMs = 8000) {
  const [slow, setSlow] = useState(false);
  useEffect(() => {
    if (!pending) return setSlow(false);
    const t = window.setTimeout(() => setSlow(true), afterMs);
    return () => window.clearTimeout(t);
  }, [pending, afterMs]);
  return slow;
}

export function useFinance(days: number, wantHealth = false) {
  const s = useSyncExternalStore(subscribe, () => state);
  useEffect(() => {
    loadCore();
    loadForecast(days);
    if (wantHealth) loadHealth();
  }, [days, wantHealth]);
  const forecast = s.forecasts[days] ?? blank<Forecast>();
  return {
    dashboard: s.core.data?.dashboard ?? null,
    context: s.core.data?.context ?? null,
    coreLoading: s.core.phase === "idle" || s.core.phase === "loading",
    coreError: s.core.phase === "error" ? s.core.error : "",
    forecast: forecast.data,
    forecastLoading: forecast.phase === "idle" || forecast.phase === "loading",
    forecastError: forecast.phase === "error" ? forecast.error : "",
    health: s.health.data,
    reload: () => reloadAll(days),
    retryForecast: () => loadForecast(days, true),
  };
}

/** The headline health score, shared by the Overview card and the Health Score page. */
export function useHealthScore() {
  const s = useSyncExternalStore(subscribe, () => state);
  useEffect(() => loadHealth(), []);
  return { health: s.health.data, loading: s.health.phase === "idle" || s.health.phase === "loading" };
}
