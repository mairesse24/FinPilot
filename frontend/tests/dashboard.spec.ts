import { expect, test } from "@playwright/test";

test("missing history shows abstention without fabricated balances", async ({ page }) => {
  await page.route("**/api/forecast?days=*", route => route.fulfill({ contentType: "application/json", body: JSON.stringify({
    status: "abstained", days: 30, series: [], projected_low: null, safety_buffer: 500, shortfall: false,
    assumptions: [], meta: { source: "baseline", as_of: "2026-11-07", warning: "Forecast abstained: provide transaction history." }
  }) }));
  // Dashboard calculation can include a cold model import. Wait for the actual
  // dependency instead of racing its response against the five-second assertion.
  await Promise.all([
    page.waitForResponse(r => r.url().endsWith('/api/dashboard') && r.status() === 200),
    page.goto("/")
  ]);
  await expect(page.getByRole("alert").filter({ hasText: "Forecast abstained" })).toBeVisible();
  await expect(page.getByText("Ending checking", { exact: true })).toHaveCount(0);
});

test("dashboard matches API and forecast controls fetch each horizon", async ({
  page,
  request,
}) => {
  const api = await request.get("/api/dashboard");
  expect(api.ok()).toBeTruthy();
  const dashboard = await api.json();
  const currency = (n: number) =>
    new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" }).format(n);
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Accounts", exact: true })).toBeVisible();
  await expect(
    page.locator(".live-panel").filter({ has: page.getByText("Net worth", { exact: true }) }),
  ).toContainText(currency(dashboard.net_worth));
  const accounts = page
    .locator(".live-panel")
    .filter({ has: page.getByRole("heading", { name: "Accounts", exact: true }) });
  for (const a of dashboard.accounts)
    await expect(accounts.locator(".live-row").filter({ hasText: a.name })).toContainText(
      currency(a.balance),
    );
  // Each horizon is fetched once; revisiting a horizon reuses the cached result (no loading flash).
  const forecasts: Record<number, any> = {};
  const requested: Record<number, number> = {};
  page.on("request", (r) => {
    const m = r.url().match(/\/api\/forecast\?days=(\d+)$/);
    if (m) requested[Number(m[1])] = (requested[Number(m[1])] ?? 0) + 1;
  });
  page.on("response", async (r) => {
    const m = r.url().match(/\/api\/forecast\?days=(\d+)$/);
    if (m && r.status() === 200) forecasts[Number(m[1])] = await r.json();
  });
  await page.reload();
  await expect(page.getByRole("heading", { name: "Accounts", exact: true })).toBeVisible();
  for (const days of [7, 90, 30]) {
    await page.getByRole("button", { name: `${days} days`, exact: true }).click();
    await expect.poll(() => forecasts[days]?.series?.length).toBe(days);
    const result = forecasts[days];
    await expect(page.getByText(`Daily forecast · ${days} days`, { exact: true })).toBeVisible();
    await page.getByText(`Daily forecast · ${days} days`, { exact: true }).click();
    await expect(page.locator("tbody tr")).toHaveCount(days);
    await expect(page.locator("tbody tr").last()).toContainText(
      currency(result.series[days - 1].projected_balance),
    );
  }
  // 30 days was loaded first and revisited last: still exactly one request per horizon.
  expect(requested).toEqual({ 7: 1, 30: 1, 90: 1 });
  await page.getByRole("link", { name: "Forecasts", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Forecasts", exact: true })).toBeVisible();
});

test("backend errors show a recovery action rather than dummy balances", async ({ page }) => {
  await page.route("**/api/dashboard", (route) =>
    route.fulfill({ status: 503, contentType: "application/json", body: "{}" }),
  );
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Dashboard unavailable" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Retry", exact: true })).toBeVisible();
  await expect(page.getByText("$24,850", { exact: true })).toHaveCount(0);
});

test("below-buffer forecasts display an explicit warning", async ({ page }) => {
  await page.route("**/api/forecast?days=*", (route) =>
    route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        days: 30,
        shortfall: true,
        safety_buffer: 500,
        projected_low: { date: "2026-11-09", balance: 100 },
        assumptions: ["Synthetic test fixture"],
        meta: { source: "baseline", as_of: "2026-11-07", warning: null },
        series: [
          { date: "2026-11-08", predicted_spend: 50, projected_balance: 100, low: 0, high: 200 },
        ],
      }),
    }),
  );
  await page.goto("/");
  await expect(page.getByRole("alert").filter({ hasText: "Cash-shortage warning" })).toBeVisible();
});
