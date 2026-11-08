import { expect, test, type Page } from "@playwright/test";

const alert = {
  id: "low_balance:test", rule: "low_balance", title: "Low Balance", severity: "high",
  cause: "Projected checking falls below your chosen buffer.",
  recommended_action: "Compare the suggested spending scenario while preserving essential payments.",
  numbers: { projected_low: 358.5, buffer: 500, first_breach_date: "2026-11-14", low_date: "2026-11-17" },
  suggested_scenario: { type: "spending_cut", reduction_amount: 150, horizon_days: 10, category: null },
};
const outcome = (low: number, end: number, score: number) => ({
  projected_low: { date: "2026-11-17", balance: low }, end_balance: end, health_score: score, alerts: [],
});
const simulation = {
  baseline: outcome(358.5, 3747.24, 77.51), scenario: outcome(508.5, 3897.24, 79.87),
  delta: { low_balance_change: 150 }, meta: { source: "baseline", as_of: "2026-11-07", warning: null },
};

async function withAlert(page: Page, request: any) {
  const dashboard = await (await request.get("/api/dashboard")).json();
  dashboard.active_alerts = [alert];
  await page.route("**/api/dashboard", (r) => r.fulfill({ json: dashboard }));
}

test("Guardian suggests a fix and shows before and after when tested", async ({ page, request }) => {
  await withAlert(page, request);
  let body: any;
  await page.route("**/api/simulate", (r) => { body = r.request().postDataJSON(); return r.fulfill({ json: simulation }); });
  await page.goto("/#/guardian");
  await expect(page.getByRole("heading", { name: "Alerts and suggested fixes" })).toBeVisible();
  await expect(page.getByText("Drops below your $500.00 buffer on Nov 14")).toBeVisible();
  await expect(page.getByText("Cut spending by $150.00 over the next 10 days", { exact: false })).toBeVisible();
  await page.getByRole("button", { name: "Test this fix" }).click();
  await expect(page.getByText("This change keeps checking above your $500.00 safety buffer.")).toBeVisible();
  await expect(page.getByRole("cell", { name: "$358.50 · Nov 17" })).toBeVisible();
  await expect(page.getByRole("cell", { name: "$508.50 · Nov 17" })).toBeVisible();
  await expect(page.getByText("Hypothetical only. Your accounts are not changed.")).toBeVisible();
  expect(body).toEqual({ scenario: alert.suggested_scenario });
});

test("a failed simulation shows an error and can be retried", async ({ page, request }) => {
  await withAlert(page, request);
  let calls = 0;
  await page.route("**/api/simulate", (r) => {
    calls += 1;
    return calls === 1 ? r.fulfill({ status: 500, json: {} }) : r.fulfill({ json: simulation });
  });
  await page.goto("/#/guardian");
  await page.getByRole("button", { name: "Test this fix" }).click();
  await expect(page.getByRole("alert").filter({ hasText: "could not run" })).toBeVisible();
  await page.getByRole("button", { name: "Try again" }).click();
  await expect(page.getByText("keeps checking above")).toBeVisible();
});

test("routes show distinct content and data is fetched once", async ({ page }) => {
  let dashboardCalls = 0;
  page.on("request", (r) => { if (r.url().endsWith("/api/dashboard")) dashboardCalls += 1; });
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Accounts", exact: true })).toBeVisible();
  await expect(page.getByRole("heading", { name: /Guardian · 30-day outlook/ })).toBeVisible();
  await page.getByRole("link", { name: "My Finances", exact: true }).click();
  await expect(page.getByRole("heading", { name: "My Finances", exact: true })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Spending by category · 30 days" })).toBeVisible();
  await expect(page.getByRole("heading", { name: /Guardian/ })).toHaveCount(0);
  await expect(page.getByRole("heading", { name: "Predictive spending & cash flow" })).toHaveCount(0);
  await page.getByRole("link", { name: "Guardian", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Accounts", exact: true })).toHaveCount(0);
  await expect(page.getByRole("heading", { name: "Predictive spending & cash flow" })).toBeVisible();
  await page.getByRole("link", { name: "Overview", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Accounts", exact: true })).toBeVisible();
  expect(dashboardCalls).toBe(1);
});

test("the forecast chart names its lowest point and the buffer", async ({ page }) => {
  await page.goto("/#/forecasts");
  const chart = page.getByRole("img", { name: /Checking balance forecast for 30 days\. Lowest projected balance/ });
  await expect(chart).toBeVisible();
  await expect(chart).toContainText("safety buffer");
  await expect(page.locator("svg text", { hasText: /^Lowest: / })).toBeVisible();
});

test("the spending-cut tool on Digital Twin validates its inputs", async ({ page }) => {
  await page.goto("/#/digital-twin");
  await expect(page.getByRole("heading", { name: "Test a spending cut" })).toBeVisible();
  await page.getByLabel("Amount to cut (USD)").fill("0");
  await expect(page.getByRole("button", { name: "Run spending-cut scenario" })).toBeDisabled();
  await expect(page.getByText("Enter an amount above $0")).toBeVisible();
  await page.getByLabel("Amount to cut (USD)").fill("200");
  await page.getByLabel("Over how many days (1–90)").fill("10");
  await page.getByRole("button", { name: "Run spending-cut scenario" }).click();
  await expect(page.getByRole("columnheader", { name: "With this change" })).toBeVisible();
});

test("the daily table lists scheduled income and bills", async ({ page }) => {
  await page.goto("/#/forecasts");
  await page.getByText("Daily forecast · 30 days", { exact: true }).click();
  await expect(page.getByRole("columnheader", { name: "Scheduled income / bills" })).toBeVisible();
  await expect(page.getByRole("cell", { name: /Scheduled income \+\$2,100\.00/ }).first()).toBeVisible();
});

test("the Economic pages still load when one data endpoint is missing", async ({ page }) => {
  await page.route("**/api/financial-inputs", (r) => r.fulfill({ status: 404, json: { detail: "Not Found" } }));
  await page.goto("/#/health-score");
  await expect(page.getByRole("heading", { name: "Your financial health" })).toBeVisible();
  await expect(page.getByText("Not Found")).toHaveCount(0);
});

test("a failed first load can be retried", async ({ page }) => {
  let calls = 0;
  await page.route("**/api/dashboard", (r) => {
    calls += 1;
    return calls === 1 ? r.fulfill({ status: 503, json: {} }) : r.continue();
  });
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Dashboard unavailable" })).toBeVisible();
  await page.getByRole("button", { name: "Retry", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Accounts", exact: true })).toBeVisible();
});

test("a slow server shows a waking-up notice, then the data", async ({ page }) => {
  await page.clock.install();
  let release!: () => void;
  const gate = new Promise<void>((resolve) => (release = resolve));
  await page.route("**/api/dashboard", async (r) => {
    await gate;
    await r.continue();
  });
  await page.goto("/");
  await expect(page.getByText("Loading your financial snapshot…")).toBeVisible();
  await expect(page.getByText(/may be waking up/)).toHaveCount(0);
  await page.clock.fastForward(9000);
  await expect(page.getByText(/may be waking up/)).toBeVisible();
  release();
  await expect(page.getByRole("heading", { name: "Accounts", exact: true })).toBeVisible();
});

test("the spending-cut form keeps what the user typed and clears stale results", async ({ page }) => {
  let release!: () => void;
  const gate = new Promise<void>((resolve) => (release = resolve));
  await page.route("**/api/dashboard", async (r) => {
    await gate;
    await r.continue();
  });
  await page.goto("/#/digital-twin");
  const amount = page.getByLabel("Amount to cut (USD)");
  await amount.fill("0.5"); // a cent-level amount is valid
  await expect(page.getByRole("button", { name: "Run spending-cut scenario" })).toBeEnabled();
  await amount.fill("200");
  const loaded = page.waitForResponse((r) => r.url().endsWith("/api/dashboard"));
  release();
  await loaded;
  await page.waitForTimeout(300);
  await expect(amount).toHaveValue("200"); // late suggestions must not overwrite it
  await page.getByLabel("Over how many days (1–90)").fill("0");
  await expect(page.getByText("Enter an amount above $0")).toBeVisible();
  await page.getByLabel("Over how many days (1–90)").fill("10");
  await page.getByRole("button", { name: "Run spending-cut scenario" }).click();
  await expect(page.getByText("Result for: Cut spending by $200.00 over the next 10 days")).toBeVisible();
  await amount.fill("300");
  await expect(page.getByText("Result for:")).toHaveCount(0); // a result never outlives its inputs
});
