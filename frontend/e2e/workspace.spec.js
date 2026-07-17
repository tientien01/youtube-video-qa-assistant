import { expect, test } from '@playwright/test'
import { readFile } from 'node:fs/promises'
import { createServer } from 'node:http'
import { extname } from 'node:path'

let staticServer
const distRoot = new URL('../dist/', import.meta.url)

test.beforeAll(async () => {
  staticServer = createServer(async (request, response) => {
    const pathname = new URL(request.url, 'http://127.0.0.1').pathname
    const relativePath = pathname === '/' || !extname(pathname) ? 'index.html' : pathname.slice(1)
    try {
      const body = await readFile(new URL(relativePath, distRoot))
      const contentType = relativePath.endsWith('.js') ? 'text/javascript' : relativePath.endsWith('.css') ? 'text/css' : 'text/html'
      response.writeHead(200, { 'Content-Type': contentType })
      response.end(body)
    } catch {
      response.writeHead(404)
      response.end()
    }
  })
  await new Promise((resolve) => staticServer.listen(4173, '127.0.0.1', resolve))
})

test.afterAll(async () => {
  await new Promise((resolve, reject) => staticServer.close((error) => error ? reject(error) : resolve()))
})

const video = {
  video_id: 'demo-video',
  title: 'Grounded retrieval walkthrough',
  channel_title: 'Local Learning Lab',
  duration_seconds: 180,
  transcript_language: 'en',
  chunk_count: 8,
  status: 'ready',
}

const transcript = {
  video_id: video.video_id,
  language_code: 'en',
  segments: [
    { segment_id: 'segment-1', original_text: 'Retrieval starts with exact transcript evidence.', start_seconds: 5, end_seconds: 12 },
    { segment_id: 'segment-2', original_text: 'The answer keeps a timestamp back to its source.', start_seconds: 12, end_seconds: 20 },
  ],
}

const source = {
  chunk_id: 'chunk-1',
  text: 'Retrieval starts with exact transcript evidence.',
  start_seconds: 5,
  end_seconds: 12,
}

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => {
    window.YT = {
      Player: class {
        constructor(id) {
          document.getElementById(id).textContent = 'YouTube video preview'
        }
        getCurrentTime() { return window.__seekSeconds || 0 }
        seekTo(seconds) { window.__seekSeconds = seconds }
        playVideo() { window.__playerStarted = true }
        destroy() {}
      },
    }
  })
  await page.route('**/api/v1/**', async (route) => {
    const request = route.request()
    const path = new URL(request.url()).pathname
    const json = (body, status = 200) => route.fulfill({ status, contentType: 'application/json', body: JSON.stringify(body) })
    if (path.endsWith('/health')) return json({
      status: 'degraded',
      api: { status: 'available', label: 'API' },
      sqlite: { status: 'available', label: 'SQLite' },
      vector_index: { status: 'available', label: 'Vector index', provider: 'chroma' },
      llm: { status: 'unavailable', label: 'LLM', provider: 'ollama', model: 'qwen2.5-coder:7b', detail: 'Provider offline' },
      database_size_bytes: 4096,
    })
    if (path.endsWith('/videos')) return json([video])
    if (path.endsWith(`/videos/${video.video_id}/transcript`)) return json(transcript)
    if (path.endsWith(`/videos/${video.video_id}`)) return json(video)
    if (path.endsWith(`/chat/history/${video.video_id}`)) return json({
      messages: [
        { message_id: 'answer-1', question: 'How is retrieval grounded?', answer: 'It starts from exact transcript evidence.', sources: [source], generation: { fallback_reason: 'Ollama is offline.' } },
        { message_id: 'answer-2', question: 'What is outside the video?', answer: 'The transcript does not provide enough evidence.', sources: [] },
      ],
    })
    if (path.endsWith('/ingest-jobs/job-failed')) return json({
      job_id: 'job-failed', video_id: video.video_id, status: 'failed', stage: 'embedding', retryable: true,
      attempt_count: 1, created_at: '2026-07-17T00:00:00Z', updated_at: '2026-07-17T00:00:02Z',
      error: { code: 'provider_unavailable', message: 'Ollama embedding model is unavailable.' },
    })
    if (path.endsWith('/ingest-jobs/job-running')) return json({
      job_id: 'job-running', video_id: video.video_id, status: 'running', stage: 'embedding', retryable: false,
      attempt_count: 1, created_at: '2026-07-17T00:00:00Z', updated_at: '2026-07-17T00:00:02Z', error: null,
    })
    return json({ detail: `Unhandled test API: ${request.method()} ${path}` }, 404)
  })
})

test('synchronizes citations, evidence, transcript, and player in the desktop workspace', async ({ page }) => {
  await page.setViewportSize({ width: 1680, height: 960 })
  await page.goto(`/library/${video.video_id}`)

  await expect(page.getByRole('heading', { name: video.title })).toBeVisible()
  await expect(page.getByText('Provider unavailable: Ollama is offline.')).toBeVisible()
  await expect(page.getByText('Insufficient transcript evidence.')).toBeVisible()
  await page.getByRole('region', { name: 'Ask this video' }).getByRole('button', { name: '00:05' }).click()
  await expect(page.locator('.evidence-card.selected')).toContainText(source.text)
  await expect(page.locator('.transcript-row.selected')).toContainText(source.text)
  await expect.poll(() => page.evaluate(() => window.__seekSeconds)).toBe(5)
  await page.screenshot({ path: 'e2e/screenshots/workspace-desktop.png', fullPage: true })
})

test('keeps the workspace usable without horizontal overflow on mobile', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 })
  await page.goto(`/library/${video.video_id}`)
  await expect(page.getByRole('region', { name: 'Transcript' })).toBeVisible()
  await expect.poll(() => page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth)).toBe(true)
  await page.screenshot({ path: 'e2e/screenshots/workspace-mobile.png', fullPage: true })
})

test('shows honest empty, planned, runtime-offline, and retryable ingest states', async ({ page }) => {
  await page.addInitScript(() => localStorage.setItem('youtube-qa-active-ingest-job', 'job-failed'))
  await page.goto('/')
  await expect(page.getByText('Degraded')).toBeVisible()
  await expect(page.getByText('Ollama embedding model is unavailable.')).toBeVisible()
  await expect(page.getByRole('button', { name: 'Retry' })).toBeVisible()
  await expect(page.getByRole('button', { name: 'Flashcards' })).toBeDisabled()
  await page.screenshot({ path: 'e2e/screenshots/ingest-failed.png', fullPage: true })
})

test('shows an explicit empty library', async ({ page }) => {
  await page.route('**/api/v1/videos', (route) => route.fulfill({ status: 200, contentType: 'application/json', body: '[]' }))
  await page.goto('/library')
  await expect(page.getByText('No ingested videos yet.')).toBeVisible()
  await page.screenshot({ path: 'e2e/screenshots/library-empty.png', fullPage: true })
})

test('shows the real active ingest stage and cancellation action', async ({ page }) => {
  await page.addInitScript(() => localStorage.setItem('youtube-qa-active-ingest-job', 'job-running'))
  await page.goto('/')
  await expect(page.getByText('Creating embeddings')).toBeVisible()
  await expect(page.getByRole('button', { name: 'Cancel' })).toBeVisible()
  await page.screenshot({ path: 'e2e/screenshots/ingest-running.png', fullPage: true })
})
