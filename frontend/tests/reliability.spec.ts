import { expect, test } from '@playwright/test';

test('repeated warning payloads become one friendly notice with expandable diagnostics', async ({ page, request }) => {
  const dashboard = await (await request.get('/api/dashboard')).json();
  const forecast = await (await request.get('/api/forecast?days=30')).json();
  const technical = 'Spending occurs much more frequently than in training data; using an unvalidated rolling-average fallback instead of the synthetic-calendar model.';
  const notice = { code: 'forecast_pattern_shift', context: 'analysis', category: 'critical',
    message: "Your recent spending pattern differs from the model's training data, so we're using a simpler estimate. Forecast confidence is limited.", technical_detail: technical };
  dashboard.meta.notices = [notice, notice]; forecast.meta.notices = [notice];
  dashboard.meta.warning = technical; forecast.meta.warning = technical;
  await page.route('**/api/dashboard', r => r.fulfill({ json: dashboard }));
  await page.route('**/api/forecast?days=*', r => r.fulfill({ json: forecast }));
  await page.goto('/');
  await expect(page.locator('[data-notice-code="forecast_pattern_shift"]')).toHaveCount(1);
  await expect(page.getByText(technical, { exact: true })).not.toBeVisible();
  await page.getByText('Engineering diagnostics', { exact: true }).click();
  await expect(page.getByText(technical, { exact: true })).toBeVisible();
  await expect(page.getByText(technical, { exact: true })).toHaveCount(1);
  await page.getByRole('link', { name: 'FinPilot Wrapped', exact: true }).click();
  await expect(page.locator('[data-notice-code="forecast_pattern_shift"]')).toHaveCount(1);
});
