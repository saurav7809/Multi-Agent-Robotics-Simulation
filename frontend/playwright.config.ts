import { defineConfig } from '@playwright/test'
import { fileURLToPath } from 'node:url'

const backend = fileURLToPath(new URL('../backend/', import.meta.url))
const python = fileURLToPath(new URL(process.platform === 'win32' ? '../.venv/Scripts/python.exe' : '../.venv/bin/python', import.meta.url))
const api = 'http://127.0.0.1:8099'
const frontend = 'http://127.0.0.1:5199'

export default defineConfig({
  testDir: './e2e',
  workers: 1,
  use: {
    baseURL: frontend,
    viewport: { width: 1440, height: 1050 },
    screenshot: 'only-on-failure',
    launchOptions: { executablePath: process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE },
  },
  webServer: [
    { command: `"${python}" -m uvicorn app.main:app --host 127.0.0.1 --port 8099`, cwd: backend, url: `${api}/api/health` },
    { command: 'npm run dev -- --port 5199', url: frontend, env: { SWARM_BACKEND_URL: api } },
  ],
})
