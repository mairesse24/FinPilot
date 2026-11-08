import { expect, test } from "@playwright/test";

test("floating chat works from overview and identifies its delivery mode", async ({
  page,
}) => {
  await page.goto("/");
  await page.getByRole("button", { name: "Open FinPilot chat", exact: true }).click();
  const chat = page.getByRole("dialog", { name: "FinPilot chat", exact: true });
  await expect(chat).toBeVisible();
  await chat
    .getByLabel("Message FinPilot", { exact: true })
    .fill("Explain my financial health score");
  await chat.getByRole("button", { name: "Send FinPilot message", exact: true }).click();
  await expect(chat.getByText(/financial.health.*out of 100/i)).toBeVisible({ timeout: 30000 });
  await expect(chat.getByRole("status")).toContainText(/Live Gemini|Live AI unavailable/);
  await page.keyboard.press("Escape");
  await expect(chat).not.toBeVisible();
  await expect(page.getByRole("button", { name: "Open FinPilot chat", exact: true })).toBeFocused();
});

test("credit failure is shown explicitly in chat rather than claiming live AI answered", async ({
  page,
}) => {
  await page.route("**/api/chat", (r) =>
    r.fulfill({
      json: {
        reply: "A local explanation based on verified calculations.",
        delivery: {
          mode: "fallback",
          provider: "openai",
          model: "gpt-4.1-mini",
          code: "quota_exhausted",
          message: "The AI provider reports exhausted credits or a spending limit.",
        },
      },
    }),
  );
  await page.goto("/");
  await page.getByRole("button", { name: "Open FinPilot chat", exact: true }).click();
  const chat = page.getByRole("dialog", { name: "FinPilot chat", exact: true });
  await chat.getByLabel("Message FinPilot", { exact: true }).fill("Explain my balances");
  await chat.getByRole("button", { name: "Send FinPilot message", exact: true }).click();
  await expect(chat.getByRole("status")).toContainText("Live AI unavailable");
  await expect(chat.getByRole("status")).toContainText("exhausted credits");
  await expect(chat.getByRole("link", { name: "Review API billing" })).toBeVisible();
});

test("confirmed score survives page navigation and is available to floating chat", async ({
  page,
}) => {
  await page.goto("/#/health-score");
  await page.getByRole("button", { name: "Improve estimate accuracy", exact: true }).click();
  await expect(page.getByLabel("Monthly take-home income", { exact: true })).toBeFocused();
  for (const [label, value] of [
    ["Monthly take-home income", "4200"],
    ["Monthly essential cash expenses", "1900"],
    ["Monthly discretionary cash expenses", "400"],
    ["Monthly required debt payments", "185"],
    ["Accessible emergency savings", "600"],
  ])
    await page.getByLabel(label, { exact: true }).fill(value);
  await page.getByRole("checkbox", { name: /I confirm upcoming bills/ }).check();
  await page.getByRole("checkbox", { name: /I confirm debt-payment/ }).check();
  await page.getByRole("button", { name: "Calculate assessment", exact: true }).click();
  await expect(page.getByRole("status")).toContainText("Assessment updated");
  const ring = page.getByRole("img", { name: /Financial health score: .* out of 100/ });
  await expect(ring).toBeVisible();
  const label = await ring.getAttribute("aria-label");
  await page.getByRole("link", { name: "Overview", exact: true }).click();
  await page.getByRole("button", { name: "Open FinPilot chat", exact: true }).click();
  const chat = page.getByRole("dialog", { name: "FinPilot chat", exact: true });
  await expect(
    chat.getByText("Using your confirmed financial inputs for this session."),
  ).toBeVisible();
  await chat
    .getByLabel("Message FinPilot", { exact: true })
    .fill("Explain my financial health score");
  await chat.getByRole("button", { name: "Send FinPilot message", exact: true }).click();
  await expect(chat.getByText(/65\.81(?:\/100|.*out of 100)/i)).toBeVisible({
    timeout: 15000,
  });
  await chat.getByRole("button", { name: "Close FinPilot chat" }).click();
  await page.getByRole("link", { name: "Health Score", exact: true }).click();
  await expect(page.getByRole("img", { name: label! })).toBeVisible();
});

test("floating chat fits a narrow mobile screen", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");
  await page.getByRole("button", { name: "Open FinPilot chat", exact: true }).click();
  await expect(page.getByRole("dialog", { name: "FinPilot chat", exact: true })).toBeVisible();
  expect(
    await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth),
  ).toBeTruthy();
});

test("floating chat launcher is a compact circle", async ({ page }) => {
  await page.goto("/");
  const launcher = page.getByRole("button", { name: "Open FinPilot chat", exact: true });
  const box = await launcher.boundingBox();
  expect(box).not.toBeNull();
  expect(Math.abs(box!.width - box!.height)).toBeLessThanOrEqual(2);
  expect(box!.width).toBeLessThanOrEqual(52);
});
