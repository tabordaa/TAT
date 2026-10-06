import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// The dev proxy makes the browser see ONE origin (localhost:5173) for both the
// app and the API, exactly like the Vercel rewrite will in production.
// Same origin => the HttpOnly cookie is first-party and SameSite=Lax just works.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        // 127.0.0.1 (not "localhost"): on Windows Node may resolve localhost to
        // IPv6 (::1) while uvicorn listens on IPv4 -> ECONNREFUSED.
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ''),
      },
    },
  },
})
