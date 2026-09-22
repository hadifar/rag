import path from 'node:path'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],

  resolve: {
    alias: [
      // @chatui/core's package.json "browser" field points at its UMD bundle,
      // which lacks ESM interop markers and makes Vite resolve `import Chat
      // from '@chatui/core'` to the whole exports object instead of the
      // component. Force resolution to the real ESM build instead.
      // Anchored regex so it doesn't also swallow subpath imports like
      // '@chatui/core/dist/index.css'.
      {
        find: /^@chatui\/core$/,
        replacement: path.resolve(
          import.meta.dirname,
          'node_modules/@chatui/core/es/index.js',
        ),
      },
    ],
  },

  server:{
    proxy:{
      '/api': 'http://localhost:8000',
    },
  },
})
