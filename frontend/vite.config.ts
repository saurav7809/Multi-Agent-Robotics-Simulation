import react from '@vitejs/plugin-react'
import tailwind from '@tailwindcss/vite'
import { defineConfig } from 'vite'

const backend = process.env.SWARM_BACKEND_URL ?? 'http://127.0.0.1:8000'
const proxy = { '/api': backend, '/ws': { target: backend, ws: true } }

export default defineConfig({
  plugins: [react(), tailwind()],
  server: { host: '127.0.0.1', port: 5173, strictPort: true, proxy },
  preview: { host: '127.0.0.1', port: 4173, strictPort: true, proxy },
})
