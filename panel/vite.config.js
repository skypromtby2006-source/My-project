import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// En desarrollo (scripts/panel_dev.sh) Vite sirve el panel en :5173 y reenvía /api
// al servidor real en :8000, WebSocket incluido. En producción no hace falta: FastAPI
// sirve el panel compilado desde el mismo origen.
export default defineConfig({
  plugins: [react()],
  server: {
    host: true,
    proxy: { '/api': { target: 'http://127.0.0.1:8000', ws: true } },
  },
})
