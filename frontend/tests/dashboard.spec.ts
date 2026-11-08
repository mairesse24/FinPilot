import { expect, test } from "@playwright/test";

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
  for (const days of [7, 90, 30]) {
    const response = page.waitForResponse(
      (r) => r.url().endsWith(`/api/forecast?days=${days}`) && r.status() === 200,
    );
    await page.getByRole("button", { name: `${days} days`, exact: true }).click();
    const result = await (await response).json();
    expect(result.series).toHaveLength(days);
    await expect(page.getByText(`Daily forecast · ${days} days`, { exact: true })).toBeVisible();
    await page.getByText(`Daily forecast · ${days} days`, { exact: true }).click();
    await expect(page.locator("tbody tr")).toHaveCount(days);
    await expect(page.locator("tbody tr").last()).toContainText(
      currency(result.series[days - 1].projected_balance),
    );
  }
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
