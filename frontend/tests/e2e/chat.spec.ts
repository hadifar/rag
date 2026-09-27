import { expect, test } from '@playwright/test';

import { signIn } from './auth.ts';

// A real LLM answers, so allow for a slow model and a retrieval round-trip.
test.setTimeout(90_000);

test('asking a question streams back a sourced answer that is saved', async ({ page }) => {
  await page.goto('/chat');
  await signIn(page);
  await expect(page).toHaveURL('/chat');

  const question = 'What plans do you offer and how much do they cost?';
  const streamDone = page
    .waitForResponse('**/api/chat/stream')
    .then((response) => response.finished());

  await page.getByPlaceholder('Type a message...').fill(question);
  await page.keyboard.press('Enter');

  // A new chat gets its id from the client before anything streams.
  await expect(page).toHaveURL(/\/chat\/[0-9a-f-]{36}$/);
  const messages = page.getByRole('log', { name: 'Messages' });
  await expect(messages.getByText(question)).toBeVisible();

  expect(await streamDone).toBeNull(); // null: the body arrived in full
  await expect(page.getByLabel('Assistant is typing')).toBeHidden();
  await expect(messages).not.toContainText('Something went wrong');
  await expect(messages.getByText('📚 Sources')).toBeVisible();

  // The conversation was persisted: a reload loads it back from the backend.
  await page.reload();
  await expect(messages.getByText(question)).toBeVisible();
});
