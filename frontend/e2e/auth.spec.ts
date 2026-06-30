import { test, expect } from './fixtures';

test.use({ storageState: { cookies: [], origins: [] } });

test('login with valid credentials redirects to dashboard', async ({ page }) => {
  await page.goto('/login');
  await page.fill('#email', 'e2e@test.fincore');
  await page.fill('#password', 'TestPass123!');
  await page.getByRole('button', { name: 'Sign in' }).click();
  await page.waitForURL('**/dashboard');
  await expect(page.getByText('FinCore', { exact: true })).toBeVisible();
});

test('unauthenticated access to /dashboard redirects to /login', async ({ page }) => {
  await page.goto('/dashboard');
  await expect(page).toHaveURL(/\/login/);
});
