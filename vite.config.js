import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
  optimizeDeps: {
    // Exclude occt-import-js from Vite's pre-bundler.
    // It is loaded via a classic <script> tag in index.html instead.
    // Vite's CJS→ESM transform breaks the Emscripten WASM runtime.
    exclude: ['occt-import-js'],
  },
})
