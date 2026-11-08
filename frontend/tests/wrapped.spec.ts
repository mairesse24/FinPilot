import { expect, test } from "@playwright/test";

const money = (value: number) =>
  value.toLocaleString("en-US", { style: "currency", currency: "USD" });

test("Wrapped presents a seven-part verified financial story and opens Copilot", async ({
  page,
  request,
}) => {
  const dashboard = await (await request.get("/api/dashboard")).json();

  await page.goto("/#/finpilot-wrapped");

  await expect(page.getByRole("heading", { name: "Your FinPilot snapshot" })).toBeVisible();
  await expect(page.locator(".wrapped-slide")).toHaveCount(7);
  await expect(page.getByText(money(dashboard.net_worth), { exact: true }).first()).toBeVisible();
  await expect(page.getByText(money(dashboard.spending_30d), { exact: true })).toBeVisible();
  await expect(page.getByText("Top spending categories", { exact: true })).toBeVisible();
  await expect(page.locator(".wrapped-category-row")).toHaveCount(
    Math.min(dashboard.by_category.length, 5),
  );
  await expect(page.getByRole("button", { name: "Switch to manual slides" })).toBeVisible();
  await expect(page.getByRole("progressbar", { name: "Time remaining on this slide" })).toBeVisible();
  const headerBox = await page.locator(".topbar").boundingBox();
  const timerBox = await page.locator(".wrapped-timer-track").boundingBox();
  if (!headerBox || !timerBox) throw new Error("Header or timer was not measurable");
  expect(timerBox.y).toBeGreaterThanOrEqual(headerBox.y + headerBox.height - 1);

  await page.getByRole("button", { name: "Ask FinPilot about my next move" }).click();
  await expect(page.getByRole("dialog", { name: "FinPilot chat" })).toBeVisible();
});

test("Wrapped advances automatically and can be paused", async ({ page }) => {
  await page.goto("/#/finpilot-wrapped");
  await expect(page.getByRole("heading", { name: "Your FinPilot snapshot" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Go to Snapshot" })).toHaveAttribute(
    "aria-current",
    "step",
  );

  await page.waitForTimeout(7_500);
  await expect(page.getByRole("button", { name: "Go to Cash" })).toHaveAttribute(
    "aria-current",
    "step",
  );

  await page.getByRole("button", { name: "Switch to manual slides" }).click();
  await page.waitForTimeout(7_500);
  await expect(page.getByRole("button", { name: "Go to Cash" })).toHaveAttribute(
    "aria-current",
    "step",
  );
  await expect(page.getByRole("button", { name: "Resume automatic slides" })).toBeVisible();
});

test("holding the right mouse button temporarily pauses the timer", async ({ page }) => {
  await page.goto("/#/finpilot-wrapped");
  await expect(page.getByRole("heading", { name: "Your FinPilot snapshot" })).toBeVisible();

  const story = page.locator(".wrapped-story");
  const box = await story.boundingBox();
  if (!box) throw new Error("Wrapped story was not measurable");
  await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2);
  await page.mouse.down({ button: "right" });
  await expect(page.locator(".wrapped-timer")).toHaveClass(/held/);
  await page.waitForTimeout(7_500);
  await expect(page.getByRole("button", { name: "Go to Snapshot" })).toHaveAttribute("aria-current", "step");
  await page.mouse.up({ button: "right" });
  await expect(page.locator(".wrapped-timer")).not.toHaveClass(/held/);
});
