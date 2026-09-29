import { expect, test } from '@playwright/test';

import { signIn, testUser } from './auth.ts';

test('a signed-out visitor is sent to login and lands home after signing in', async ({ page }) => {
  await page.goto('/');
  await expect(page).toHaveURL('/login');

  await signIn(page);

  await expect(page).toHaveURL('/');
  await expect(page.getByRole('heading', { name: `Hello ${testUser.email}` })).toBeVisible();
});
