import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    // Dev: same-origin /api calls are proxied to the FastAPI server.
    // Production: CloudFront serves /api/* from the same origin.
    proxy: {
      '/api': 'http://localhost:8000',
    },
  },
})
