import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [
    react(),
    tailwindcss(),
  ],
  build: {
    outDir: 'dist',   // explicit — Render publish directory: frontend/dist
  },
  server: {
    port: 5173,
    // Dev proxy: routes API calls to the local FastAPI server.
    // In production VITE_API_URL is set instead — proxy is dev-only.
    proxy: {
      '/build-basket':  'http://localhost:8000',
      '/generate-plan': 'http://localhost:8000',
      '/health':        'http://localhost:8000',
    },
  },
})
