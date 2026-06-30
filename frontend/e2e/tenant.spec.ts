import { test, expect, getTestData } from './fixtures';

test('create a new organization and switch to it', async ({ page }) => {
  const data = getTestData();
  await page.goto('/dashboard');

  // Open tenant switcher — MenuButton shows the active tenant name
  await page.getByRole('button', { name: data.tenantName }).click();
  await page.getByText('New organization').click();

  // Step 1: fill name (slug auto-derived)
  await expect(page.locator('#org-name')).toBeVisible();
  const orgName = `E2E Org ${Date.now().toString().slice(-6)}`;
  await page.fill('#org-name', orgName);
  await page.getByRole('button', { name: 'Next', exact: true }).click();

  // Step 2: confirm
  await page.getByRole('button', { name: 'Create organization' }).click();

  // Verify the switcher now shows the new org name
  await expect(page.getByRole('button', { name: orgName })).toBeVisible({ timeout: 10_000 });
});
