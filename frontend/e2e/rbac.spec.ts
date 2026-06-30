import { test, expect } from './fixtures';

test('invite a team member', async ({ page }) => {
  await page.goto('/settings?tab=members');
  await page.getByRole('button', { name: 'Invite member' }).click();
  await expect(page.locator('#invite-email')).toBeVisible();
  await page.fill('#invite-email', 'colleague@test.fincore');
  await page.getByRole('button', { name: 'Invite' }).click();
  await expect(page.getByText('Invitation sent')).toBeVisible();
});

test('create a role with permissions', async ({ page }) => {
  const roleName = `E2E Role ${Date.now().toString().slice(-6)}`;
  await page.goto('/settings?tab=roles');
  await page.getByRole('button', { name: 'Create role' }).first().click();
  await expect(page.locator('#role-name')).toBeVisible();
  await page.fill('#role-name', roleName);
  // Check first available permission if permissions are loaded
  const firstCheckbox = page.locator('input[type="checkbox"]').first();
  if (await firstCheckbox.isVisible()) {
    await firstCheckbox.check();
  }
  // Modal confirm button is the last "Create role" button in the DOM
  await page.getByRole('button', { name: 'Create role' }).last().click();
  await expect(page.getByText('Role created')).toBeVisible();
  await expect(page.getByText(roleName)).toBeVisible();
});
