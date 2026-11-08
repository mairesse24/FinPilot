import { expect, test } from "@playwright/test";

test("account tiles show every imported savings account and loan separately", async ({
  page,
  request,
}) => {
  const dashboard = await (await request.get("/api/dashboard")).json();
  dashboard.accounts = [
    { id: "checking-1", name: "Everyday checking", account_type: "checking", balance: 1000 },
    { id: "savings-1", name: "North Bank savings", account_type: "savings", balance: 200 },
    { id: "savings-2", name: "Credit Union emergency fund", account_type: "savings", balance: 300 },
    {
      id: "loan-1",
      name: "Home mortgage",
      account_type: "loan",
      balance: 180000,
      apr: 0.065,
      min_payment: 1200,
    },
    { id: "loan-2", name: "Vehicle loan", account_type: "loan", balance: 9000 },
  ];
  dashboard.liabilities = 189000;
  dashboard.assets = 1500;
  dashboard.net_worth = -187500;
  await page.route("**/api/dashboard", (r) => r.fulfill({ json: dashboard }));
  await page.goto("/");
  await page.getByRole("button", { name: /^Net worth/ }).click();
  await expect(
    page
      .getByRole("dialog", { name: "Account details" })
      .getByText("-$187,500.00", { exact: true }),
  ).toBeVisible();
  await page.keyboard.press("Escape");
  await page.getByRole("button", { name: /^Savings/ }).click();
  const dialog = page.getByRole("dialog", { name: "Account details" });
  await expect(dialog.getByText("North Bank savings", { exact: true })).toBeVisible();
  await expect(dialog.getByText("Credit Union emergency fund", { exact: true })).toBeVisible();
  await expect(dialog.getByText("Home mortgage", { exact: true })).toHaveCount(0);
  await page.keyboard.press("Escape");
  await expect(dialog).not.toBeVisible();
  await page.getByRole("button", { name: /^Loans/ }).click();
  await expect(dialog.getByText("Home mortgage", { exact: true })).toBeVisible();
  await expect(dialog.getByText("Vehicle loan", { exact: true })).toBeVisible();
  await expect(dialog.getByText("6.50%", { exact: true })).toBeVisible();
});

test("profile and notifications show real scoped backend information", async ({
  page,
  request,
}) => {
  const context = await (await request.get("/api/context")).json();
  const guardian = await (await request.get("/api/guardian")).json();
  await page.goto("/");
  await page.getByRole("button", { name: "Profile", exact: true }).click();
  await expect(
    page
      .getByRole("region", { name: "Profile details" })
      .getByRole("heading", { name: context.user.name }),
  ).toBeVisible();
  await page.getByRole("link", { name: "View my accounts" }).click();
  await expect(page.getByRole("heading", { name: "My Finances", exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Notifications", exact: true }).click();
  const notifications = page.getByRole("region", { name: "Current notifications" });
  await expect(notifications.getByRole("heading", { name: "Financial alerts" })).toBeVisible();
  if (guardian.alerts.length)
    await expect(notifications.getByText(guardian.alerts[0].title, { exact: true })).toBeVisible();
  else await expect(notifications.getByText(/No configured alerts/)).toBeVisible();
  await expect(page.getByText(/Mission: Financial freedom/i)).toHaveCount(0);
});

test("home transaction demo evaluates an arbitrary purchase and raises a notification", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: "Simulate live transaction", exact: true }).click();
  const dialog = page.getByRole("dialog", { name: "Live transaction simulator" });
  await expect(dialog).toBeVisible();
  await dialog.getByLabel("Purchase amount", { exact: true }).fill("6200");
  await dialog.getByLabel("Description", { exact: true }).fill("Judge demo laptop");
  await dialog.getByRole("button", { name: "Run transaction simulation", exact: true }).click();
  await expect(dialog.getByRole("region", { name: "Transaction simulation result" })).toContainText("$300.00");
  await expect(dialog.getByRole("alert").first()).toContainText("Safety buffer warning");
  await expect(dialog).toContainText("nothing was executed or saved");
  await expect(page.getByLabel("New simulated alert")).toBeVisible();
});

test("assessment explains the savings limit inline, then calculates and runs a scenario", async ({
  page,
}) => {
  await page.goto("/#/health-score");
  await page.getByText("Review or correct imported assumptions", { exact: false }).click();
  await expect(page.getByText("Imported savings:", { exact: false })).toBeVisible();
  for (const [label, value] of [
    ["Monthly take-home income", "7000"],
    ["Monthly essential cash expenses", "2000"],
    ["Monthly discretionary cash expenses", "120"],
    ["Monthly required debt payments", "1500"],
    ["Accessible emergency savings", "2000"],
  ]) {
    await page.getByLabel(label, { exact: true }).fill(value);
  }
  await page.getByRole("checkbox", { name: /I confirm upcoming bills/ }).check();
  await page.getByRole("checkbox", { name: /I confirm debt-payment/ }).check();
  await page.getByRole("button", { name: "Calculate assessment", exact: true }).click();
  await expect(page.getByRole("alert")).toContainText("imported savings total of $600.00");
  await expect(page.getByLabel("Accessible emergency savings", { exact: true })).toHaveAttribute(
    "aria-invalid",
    "true",
  );
  await page.getByLabel("Accessible emergency savings", { exact: true }).fill("600");
  await expect(
    page.getByText(/of your declared monthly debt payments has no imported payment dates/),
  ).toBeVisible();
  await page.getByRole("button", { name: "Calculate assessment", exact: true }).click();
  await expect(page.getByRole("status")).toContainText(
    "Some required information is still missing",
  );
  await expect(
    page.getByRole("img", { name: /Financial health score: .* out of 100/ }),
  ).toBeVisible();
  await page.getByLabel("Monthly required debt payments", { exact: true }).fill("185");
  await page.getByRole("button", { name: "Calculate assessment", exact: true }).click();
  await expect(
    page.getByRole("img", { name: /Financial health score: .* out of 100/ }),
  ).toBeVisible();
  await page.getByRole("link", { name: "Digital Twin", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Try a what-if scenario", exact: true }),
  ).toBeVisible();
  const headings = await page.getByRole("heading", { level: 2 }).allTextContents();
  expect(headings.indexOf("Test a spending cut")).toBeLessThan(headings.indexOf("Try a what-if scenario"));
  expect(headings.some((h) => h.startsWith("Economic conditions"))).toBe(false);
  await page.getByLabel("Stress scenario", { exact: true }).selectOption("emergency_expense");
  await page.getByLabel("Stress amount", { exact: true }).fill("1000");
  await page.getByRole("button", { name: "Run hypothetical scenario", exact: true }).click();
  await expect(
    page.getByRole("img", { name: "Baseline and hypothetical checking cash plans" }),
  ).toBeVisible();
});

test("compact workspace supports mobile navigation without horizontal overflow", async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/#/digital-twin");
  await expect(
    page.getByRole("heading", { name: "Try a what-if scenario", exact: true }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Open navigation", exact: true }).click();
  await page.getByRole("link", { name: "Health Score", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Health Score", exact: true })).toBeVisible();
  expect(
    await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth),
  ).toBeTruthy();
});
