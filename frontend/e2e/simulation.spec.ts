import { expect, test, type APIRequestContext } from '@playwright/test'
import { readFile } from 'node:fs/promises'
import type { Snapshot } from '../src/types'

async function status(request: APIRequestContext) {
  return await (await request.get('/api/simulation/status')).json() as Snapshot
}

test.beforeEach(async ({ request }) => {
  await request.post('/api/scenarios/area-exploration/load')
  await request.post('/api/simulation/configure', { data: {
    seed: 42, agent_count: 10, speed: 1, width: 1000, height: 580, agent_speed: 68, communication_range: 185,
    delay_ms: 0, packet_loss: 0, update_hz: 12,
  } })
})

test('live Canvas, WebSocket and run controls', async ({ page, request }, testInfo) => {
  test.setTimeout(60_000)
  const connection = page.waitForEvent('websocket', socket => socket.url().endsWith('/ws/simulation'))
  await page.goto('/')
  await connection
  await expect(page.getByRole('status')).toContainText('Telemetry live')
  await expect(page.getByRole('heading', { name: 'Mission control' })).toBeVisible()
  const start = page.getByRole('button', { name: 'Start', exact: true })
  await expect(start).toBeEnabled()
  const before = await status(request)
  await page.getByLabel('Playback speed').selectOption('4')
  await expect.poll(async () => (await status(request)).config.speed).toBe(4)
  expect((await status(request)).run_id).toBe(before.run_id)
  await start.click()
  await expect.poll(async () => {
    const after = await status(request)
    return Math.hypot(after.agents[0].x - before.agents[0].x, after.agents[0].y - before.agents[0].y)
  }).toBeGreaterThan(15)
  const canvas = page.locator('canvas.arena-canvas')
  await expect(canvas).toBeVisible()
  await expect.poll(async () => canvas.evaluate(node => {
    const element = node as HTMLCanvasElement
    return element.getContext('2d')?.getImageData(element.width / 2, element.height / 2, 1, 1).data[3]
  })).toBe(255)
  await expect.poll(async () => (await status(request)).time).toBeGreaterThan(6)
  await page.getByLabel('Playback speed').selectOption('1')
  await page.screenshot({ path: testInfo.outputPath('live-arena.png'), fullPage: true })
  await page.getByRole('button', { name: 'Pause', exact: true }).click()
  const resume = page.getByRole('button', { name: 'Resume', exact: true })
  await expect(resume).toBeVisible()
  const paused = await status(request)

  for (const name of ['Grid', 'Links', 'Trails']) {
    const layer = page.getByRole('button', { name, exact: true })
    await layer.click()
    await expect(layer).toHaveAttribute('aria-pressed', 'false')
    await layer.click()
    await expect(layer).toHaveAttribute('aria-pressed', 'true')
  }
  await page.getByRole('button', { name: 'Zoom in' }).click()
  await expect(page.getByRole('button', { name: 'Zoom out' })).toBeEnabled()
  await page.getByRole('button', { name: 'Fit arena' }).click()
  await expect(page.getByRole('button', { name: 'Zoom out' })).toBeDisabled()

  await page.getByRole('button', { name: 'Save reference' }).click()
  await expect(page.getByRole('heading', { name: /Change from reference run/ })).toBeVisible()
  await page.getByRole('button', { name: 'Clear reference' }).click()
  expect((await status(request)).time).toBe(paused.time)
  await resume.click()
  await expect.poll(async () => (await status(request)).time).toBeGreaterThan(paused.time)
  await page.getByRole('button', { name: 'Reset', exact: true }).click()
  await expect(start).toBeEnabled()
})

test('mission setup, agent faults and exports', async ({ page, request }) => {
  await page.goto('/')
  const mission = page.getByLabel('Mission scenario')
  await mission.selectOption('search-and-rescue')
  await expect(page.getByLabel('Swarm algorithm')).toHaveValue('auction')
  await page.getByLabel('Swarm algorithm').selectOption('boids')
  const fleet = page.getByRole('slider', { name: 'Agent count' })
  await fleet.press('Home')
  await fleet.press('ArrowRight')
  await fleet.press('ArrowRight')
  await fleet.press('ArrowRight')
  await page.getByRole('slider', { name: 'Radio range' }).press('End')
  await page.getByText('Advanced settings', { exact: true }).click()
  const fields = {
    'Arena width': '800', 'Arena height': '500', 'Drone speed': '70', 'Obstacle density': '8', 'Target points': '3',
    'Duration (s)': '120', 'Packet loss (%)': '12', 'Radio delay (ms)': '140', 'Stream rate (Hz)': '8',
    'Arena seed': '212', Separation: '1.8', Alignment: '0.6', Cohesion: '0.9',
  }
  for (const [label, value] of Object.entries(fields)) await page.getByLabel(label, { exact: true }).fill(value)
  await page.getByRole('button', { name: 'Apply configuration' }).click()
  await expect.poll(async () => (await status(request)).config.algorithm).toBe('boids')
  const applied = await status(request)
  expect(applied.config).toMatchObject({
    agent_count: 8, communication_range: 700, width: 800, height: 500, agent_speed: 70, obstacle_density: 8, target_count: 3,
    duration: 120, packet_loss: 0.12, delay_ms: 140, update_hz: 8, seed: 212, separation: 1.8, alignment: 0.6, cohesion: 0.9,
  })
  await page.getByRole('button', { name: 'Randomize arena' }).click()
  await expect.poll(async () => (await status(request)).config.seed).not.toBe(212)

  const current = await status(request)
  const canvas = page.locator('canvas.arena-canvas')
  const bounds = await canvas.boundingBox()
  expect(bounds).not.toBeNull()
  if (!bounds) throw new Error('The arena has no layout box')
  const { width, height } = current.config
  const scale = Math.min((bounds.width - 54) / width, (bounds.height - 40) / height)
  await canvas.click({ position: {
    x: (bounds.width - width * scale) / 2 + current.agents[0].x * scale,
    y: (bounds.height - height * scale) / 2 + current.agents[0].y * scale,
  } })
  const agent = page.getByLabel('Select agent')
  await expect(agent).toHaveValue('1')
  await page.getByRole('button', { name: 'Disable radio' }).click()
  await expect(page.getByRole('button', { name: 'Restore radio' })).toBeEnabled()
  await page.getByRole('button', { name: 'Restore radio' }).click()
  await expect(page.getByRole('button', { name: 'Disable radio' })).toBeEnabled()
  await page.getByRole('button', { name: 'Drain battery' }).click()
  await expect.poll(async () => (await status(request)).agents[0].battery).toBe(12)
  await page.getByRole('button', { name: 'Fail agent' }).click()
  await page.getByLabel('Filter events').selectOption('fault')
  await expect(page.getByText('U-01 failed (manual fault).')).toBeVisible()
  await page.getByRole('button', { name: 'Restore agent' }).click()
  await expect.poll(async () => (await status(request)).agents[0].battery).toBe(100)
  await page.getByRole('button', { name: 'Random failure' }).click()
  await expect.poll(async () => (await status(request)).metrics.failed_agents).toBe(1)

  for (const [label, extension] of [['Metrics CSV', 'csv'], ['Full run JSON', 'json']] as const) {
    await page.getByLabel('Export results').click()
    const downloading = page.waitForEvent('download')
    await page.getByRole('link', { name: label }).click()
    const download = await downloading
    expect(download.suggestedFilename()).toMatch(new RegExp('swarm-run-\\d+\\.' + extension))
    const contents = await readFile(await download.path(), 'utf8')
    if (extension === 'csv') expect(contents).toContain('mission_progress,coverage,average_battery')
    else expect(JSON.parse(contents).snapshot.metrics.failed_agents).toBe(1)
  }
  await mission.selectOption('communication-failure')
  await expect(page.getByLabel('Swarm algorithm')).toHaveValue('consensus')
  for (const name of ['Fleet', 'Network', 'Tasks', 'Consensus']) {
    const tab = page.getByRole('button', { name, exact: true })
    await tab.click()
    await expect(tab).toHaveAttribute('aria-pressed', 'true')
  }
})

test('narrow layout keeps the arena and controls within the viewport', async ({ page }, testInfo) => {
  await page.setViewportSize({ width: 390, height: 844 })
  await page.goto('/')
  await expect(page.getByRole('heading', { name: 'Simulation arena' })).toBeVisible()
  await expect(page.getByLabel('Mission scenario')).toBeEnabled()
  await expect(page.getByRole('button', { name: 'Start', exact: true })).toBeEnabled()
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBe(390)
  await page.screenshot({ path: testInfo.outputPath('mobile-console.png'), fullPage: true })
})
