import { test, expect, getTestData } from './fixtures';

test('full loan lifecycle: create → submit → approve → disburse → repay', async ({ page }) => {
  const data = getTestData();
  await page.goto('/loans');

  // Open create modal
  await page.getByRole('button', { name: 'New application' }).click();
  await expect(page.getByText('New Loan Application')).toBeVisible();

  // Select product, fill amount and term
  await page.getByRole('dialog').getByRole('combobox').selectOption({ label: data.loanProductName });
  await page.getByPlaceholder('0.00').fill('50000');
  await page.getByPlaceholder('12').fill('12');
  await page.getByRole('button', { name: 'Submit application' }).click();
  await expect(page.getByText('Loan application created')).toBeVisible();

  // Drawer opens automatically after creation — submit for review
  await expect(page.getByRole('button', { name: 'Submit for review' })).toBeVisible();
  await page.getByRole('button', { name: 'Submit for review' }).click();
  await expect(page.getByText('Loan submitted for review')).toBeVisible();

  // Re-open drawer — approve
  // Backend approve_loan handles SUBMITTED → UNDER_REVIEW → APPROVED in one call
  await page.locator('tbody tr').first().click();
  await expect(page.getByRole('button', { name: 'Approve' })).toBeVisible({ timeout: 10_000 });
  await page.getByRole('button', { name: 'Approve' }).click();
  await expect(page.getByText('Loan approved')).toBeVisible();

  // Re-open drawer — disburse
  await page.locator('tbody tr').first().click();
  await expect(page.getByRole('button', { name: 'Disburse' })).toBeVisible({ timeout: 10_000 });
  await page.getByRole('button', { name: 'Disburse' }).click();
  await expect(page.getByText('Loan disbursed')).toBeVisible();

  // Re-open drawer — record repayment
  await page.locator('tbody tr').first().click();
  await expect(page.getByRole('button', { name: 'Record repayment' })).toBeVisible({ timeout: 10_000 });
  await page.getByRole('button', { name: 'Record repayment' }).click();
  await expect(page.getByRole('heading', { name: 'Record Repayment' })).toBeVisible();
  await page.getByPlaceholder('0.00').fill('5000');
  await page.getByRole('button', { name: 'Record payment' }).click();
  await expect(page.getByText('Payment recorded')).toBeVisible();
});
