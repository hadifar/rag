import { spawnSync } from 'node:child_process';

import { testUser } from './auth.ts';

// Runs once, after webServer is up and before any test. Needs Postgres with migrations applied.
function rag(...args: string[]) {
  return spawnSync('uv', ['run', 'rag', ...args], {
    cwd: '..',
    encoding: 'utf8',
    stdio: ['ignore', 'inherit', 'pipe'],
  });
}

export default async function globalSetup() {
  // The user the specs sign in as; on later runs it already exists, which is fine.
  const user = rag('create-user', testUser.email, '--password', testUser.password);
  if (user.status !== 0 && !user.stderr.includes('already exists')) {
    throw new Error(`rag create-user failed:\n${user.stderr}`);
  }

  // The knowledge base the chat spec expects sourced answers from.
  const ingest = rag('ingest');
  if (ingest.status !== 0) {
    throw new Error(`rag ingest failed:\n${ingest.stderr}`);
  }
}
