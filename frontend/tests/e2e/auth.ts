import type { Page } from '@playwright/test';

function requireEnv(name: string): string {
  const value = process.env[name];
  if (!value) {
    throw new Error(`${name} is not set: e2e tests sign in as an existing user (rag create-user)`);
  }
  return value;
}

export const testUser = {
  get email() {
    return requireEnv('E2E_EMAIL');
  },
  get password() {
    return requireEnv('E2E_PASSWORD');
  },
};

/** Fills in and submits the login form; the page must already be on /login. */
export async function signIn(page: Page) {
  await page.getByLabel('Email').fill(testUser.email);
  await page.getByLabel('Password').fill(testUser.password);
  await page.getByRole('button', { name: 'Sign in' }).click();
}
