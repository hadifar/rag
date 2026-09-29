/// <reference types="vitest/config" />
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],

  server:{
    proxy:{
      '/api': 'http://localhost:8000',
    },
  },

  test: {
    environment: 'jsdom',
    // A page URL, so the app's relative '/api/...' requests resolve as in the browser.
    environmentOptions: { jsdom: { url: 'http://localhost' } },
    include: ['tests/{unit,integration}/**/*.test.{ts,tsx}'],
    setupFiles: ['./tests/setup.ts'],
  },
})
