import { expect, test } from '@playwright/test';

test('expected forecast routing stays in one optional explanation without engineering noise', async ({ page, request }) => {
  const dashboard = await (await request.get('/api/dashboard')).json();
  const forecast = await (await request.get('/api/forecast?days=30')).json();
  const technical = 'Spending occurs much more frequently than in training data; using an unvalidated rolling-average fallback instead of the synthetic-calendar model.';
  const notice = { code: 'forecast_pattern_shift', context: 'analysis', category: 'data_limitation',
    message: "Your recent spending pattern differs from the model's training data, so we're using a simpler estimate. Forecast confidence is limited.", technical_detail: technical };
  dashboard.meta.notices = [notice, notice]; forecast.meta.notices = [notice];
  dashboard.meta.warning = technical; forecast.meta.warning = technical;
  await page.route('**/api/dashboard', r => r.fulfill({ json: dashboard }));
  await page.route('**/api/forecast?days=*', r => r.fulfill({ json: forecast }));
  await page.goto('/');
  await expect(page.locator('[data-notice-code="forecast_pattern_shift"]')).toHaveCount(1);
  await expect(page.getByText(notice.message, { exact: true })).not.toBeVisible();
  await expect(page.getByText(technical, { exact: true })).not.toBeVisible();
  await expect(page.getByText('Engineering diagnostics', { exact: true })).toHaveCount(0);
  await page.getByText('About this estimate', { exact: true }).click();
  await expect(page.getByText(notice.message, { exact: true })).toBeVisible();
  await expect(page.getByText(technical, { exact: true })).toHaveCount(0);
  await expect(page.locator('body')).not.toContainText('**');
  await expect(page.locator('body')).not.toContainText('&#x');
  await page.getByRole('link', { name: 'FinPilot Wrapped', exact: true }).click();
  await expect(page.locator('[data-notice-code="forecast_pattern_shift"]')).toHaveCount(1);
});
