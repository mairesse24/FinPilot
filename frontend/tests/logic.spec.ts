import { expect, test } from "@playwright/test";
import {
  alertFacts, describeCut, forecastEvents, isDebug, niceTicks, plainAssumptions,
} from "../src/dashboardLogic";

// Pure-function tests (no browser).
const row = (date: string, projected_balance: number, predicted_spend: number) => ({
  date, projected_balance, predicted_spend, low: projected_balance - 100, high: projected_balance + 100,
});

test("forecastEvents recovers scheduled bills and income from the balance series", () => {
  const series = [
    row("2026-11-08", 2360, 40), // only variable spending
    row("2026-11-09", 820, 40), // rent $1,500 due
    row("2026-11-10", 2880, 40), // paycheck $2,100
  ];
  const events = forecastEvents(series, 2400, [{ name: "Rent", amount: 1500, due_date: "2026-11-09" }]);
  expect(events).toEqual([
    { date: "2026-11-09", amount: -1500, label: "Rent" },
    { date: "2026-11-10", amount: 2100, label: "Scheduled income" },
  ]);
});

test("forecastEvents ignores sub-dollar noise and labels unknown outflows generically", () => {
  const events = forecastEvents(
    [row("2026-11-08", 2359.6, 40), row("2026-11-09", 1000, 40)], 2400, [],
  );
  expect(events).toEqual([{ date: "2026-11-09", amount: -1319.6, label: "Scheduled payments" }]);
});

test("niceTicks gives round, ascending ticks and survives flat data", () => {
  const ticks = niceTicks(311.76, 4964);
  expect(ticks[0]).toBeLessThanOrEqual(311.76);
  expect(ticks.at(-1)!).toBeGreaterThanOrEqual(4964);
  expect(ticks.every((t) => t % 500 === 0)).toBeTruthy();
  expect([...ticks].sort((a, b) => a - b)).toEqual(ticks);
  const flat = niceTicks(500, 500);
  expect(flat.length).toBeGreaterThanOrEqual(2);
  expect(flat[1]).toBeGreaterThan(flat[0]);
  expect(niceTicks(-300, 200).includes(0)).toBeTruthy();
});

test("plainAssumptions translates engineering wording and keeps raw text only for debug", () => {
  const raw = [
    "Variable-spending method: moving_average_28.",
    "Backend category vocabulary differs from PNC training data; inference may use a warned baseline fallback.",
    "Serving baseline has no applicable independent real-customer validation.",
    "Synthetic prototype; original engineering-audit findings remain relevant.",
    "Income repeats on your paydays.",
    "Internal flag forecast_unvalidated set.",
  ];
  const plain = plainAssumptions(raw);
  expect(plain).toEqual([
    "Variable spending is estimated from your recent daily spending.",
    "Some spending categories may be estimated.",
    "This forecast has not been independently validated.",
    "This prototype uses fictional demo data.",
    "Income repeats on your paydays.",
  ]);
  expect(plain.join(" ")).not.toMatch(/moving_average|PNC|engineering/);
  expect(plainAssumptions(raw, true)).toEqual(raw);
});

test("alertFacts turns alert numbers into sentences and tolerates missing values", () => {
  const base = { id: "a", title: "t", severity: "high", cause: "c", recommended_action: "r" };
  expect(
    alertFacts({ ...base, numbers: { first_breach_date: "2026-11-14", buffer: 500, projected_low: 358.5, months_covered: 1.05 } }),
  ).toEqual([
    "Drops below your $500.00 buffer on Nov 14",
    "Lowest projected balance: $358.50",
    "Savings cover 1.1 months of expenses (target: 3 months)",
  ]);
  expect(alertFacts({ ...base, numbers: { months_covered: null as unknown as number } })).toEqual([]);
  expect(alertFacts(base)).toEqual([]);
});

test("describeCut names the category when one is set; debug is off outside a browser", () => {
  expect(describeCut({ type: "spending_cut", reduction_amount: 150, horizon_days: 10 })).toBe(
    "Cut spending by $150.00 over the next 10 days",
  );
  expect(describeCut({ type: "spending_cut", reduction_amount: 50, horizon_days: 5, category: "dining" })).toBe(
    "Cut dining spending by $50.00 over the next 5 days",
  );
  expect(isDebug()).toBe(false);
});
