import assert from 'node:assert/strict'
import test from 'node:test'

import { readVideoHistory, replaceVideoHistory } from './videoStorage.js'


function installLocalStorage() {
  const values = new Map()
  globalThis.localStorage = {
    getItem: (key) => values.get(key) ?? null,
    setItem: (key, value) => values.set(key, String(value)),
    removeItem: (key) => values.delete(key),
  }
}


test('server video history replaces stale browser-only entries', () => {
  installLocalStorage()
  localStorage.setItem('youtube-qa-video-history', JSON.stringify([
    { video_id: 'stale-video', title: 'Stale video' },
  ]))

  const history = replaceVideoHistory([
    { video_id: 'canonical-video', title: 'Canonical video', updated_at: '2026-07-19T00:00:00Z' },
  ])

  assert.deepEqual(history.map((video) => video.video_id), ['canonical-video'])
  assert.deepEqual(readVideoHistory(), history)
})
