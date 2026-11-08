import { expect, test } from '@playwright/test';

test('economic page displays classification and household inflation impact without duplicating health', async ({ page, request }) => {
  const response = await request.get('/api/economy');
  expect(response.ok()).toBeTruthy();
  const economy = await response.json();
  await page.goto('/#/economic-lab');
  await expect(page.getByRole('heading', { name: `Economic conditions · ${economy.as_of}` })).toBeVisible();
  await expect(page.getByText(economy.status, { exact: true })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Inflation impact on your cash flow' })).toBeVisible();
  await expect(page.getByText('Automatic financial health estimate', { exact: true })).toHaveCount(0);
  await expect(page.getByRole('heading', { name: 'Try a what-if scenario' })).toHaveCount(0);
  expect(economy.method).not.toContain('accuracy');
});

test('confirmed synthetic customer facts produce actual score and deterministic stress', async ({ page, request }) => {
  // Uses the existing fictional Nessie demo's explicit rent/utilities/card/loan schedules.
  const facts = { take_home_income: 4200, essential_cash_expenses: 1900, discretionary_cash_expenses: 400,
    required_debt_payments: 185, accessible_emergency_savings: 600, bills_complete: true, debt_complete: true };
  const api = await request.post('/api/financial-health/assess', { data: { facts } });
  expect(api.ok()).toBeTruthy();
  const health = await api.json();
  expect(health.score).not.toBeNull();
  await page.goto('/#/health-score');
  await page.getByText('Review or correct imported assumptions', { exact: false }).click();
  for (const [label, value] of [['Monthly take-home income', '4200'], ['Monthly essential cash expenses', '1900'],
    ['Monthly discretionary cash expenses', '400'], ['Monthly required debt payments', '185'], ['Accessible emergency savings', '600']]) {
    await page.getByLabel(label, { exact: true }).fill(value);
  }
  await page.getByRole('checkbox', { name: /I confirm upcoming bills/ }).check();
  await page.getByRole('checkbox', { name: /I confirm debt-payment/ }).check();
  await page.getByRole('button', { name: 'Calculate assessment', exact: true }).click();
  await expect(page.getByText(`${health.score.toFixed(2)} / 100`, { exact: true })).toBeVisible();
  await page.getByRole('link', { name: 'Digital Twin', exact: true }).click();
  await page.getByLabel('Stress scenario', { exact: true }).selectOption('emergency_expense');
  await page.getByLabel('Stress amount', { exact: true }).fill('1000');
  await page.getByRole('button', { name: 'Run hypothetical scenario', exact: true }).click();
  await expect(page.getByRole('img', { name: 'Baseline and hypothetical checking cash plans' })).toBeVisible();
  await expect(page.getByText('-$1,000.00', { exact: true })).toHaveCount(2);
  await expect(page.getByText('Automatic financial health estimate', { exact: true })).toHaveCount(0);
  await page.getByRole('link', { name: 'AI Co-Pilot', exact: true }).click();
  await page.getByLabel('Financial question', { exact: true }).fill('Why is my v2 score what it is?');
  await page.getByRole('button', { name: 'Ask with confirmed inputs', exact: true }).click();
  await expect(page.getByText(`FinPilot v2 score: ${health.score}/100.`, { exact: false })).toBeVisible();
});
