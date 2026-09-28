import { defineConfig, devices } from '@playwright/test';

// End-to-end against the real stack: Vite serves the UI and proxies /api to the backend,
// which needs Postgres up, migrations applied and an LLM key in ../.env (see docs/setup.md).
export default defineConfig({
  testDir: './tests/e2e',
  globalSetup: './tests/e2e/global-setup.ts',
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  reporter: 'list',
  use: {
    baseURL: 'http://localhost:5173',
    trace: 'retain-on-failure',
  },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
  webServer: [
    {
      command: 'uv run rag serve',
      cwd: '..',
      url: 'http://localhost:8000/api/health/ready',
      reuseExistingServer: !process.env.CI,
    },
    {
      command: 'npm run dev',
      url: 'http://localhost:5173',
      reuseExistingServer: !process.env.CI,
    },
  ],
});
