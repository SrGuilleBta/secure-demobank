import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Servidor de desarrollo (npm run dev): manda /api al proxy del stack, así el frontend y la API
// comparten origen igual que en producción (sin CORS).
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': 'http://localhost:8080',
    },
  },
})
