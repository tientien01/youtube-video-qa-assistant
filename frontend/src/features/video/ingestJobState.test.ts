import assert from 'node:assert/strict'
import test from 'node:test'

import { ACTIVE_INGEST_STATUSES, availableJobAction } from './ingestJobState.ts'

const baseJob = {
  job_id: 'job-1',
  video_id: 'video-1',
  stage: 'pending' as const,
  target_fingerprint: null,
  retryable: false,
  error: null,
  created_at: '2026-07-17T00:00:00Z',
  started_at: null,
  finished_at: null,
}

test('classifies every active and terminal ingest state', () => {
  assert.deepEqual([...ACTIVE_INGEST_STATUSES], ['pending', 'running', 'retry_wait'])
  assert.equal(availableJobAction({ ...baseJob, status: 'pending' }), 'cancel')
  assert.equal(availableJobAction({ ...baseJob, status: 'running' }), 'cancel')
  assert.equal(availableJobAction({ ...baseJob, status: 'retry_wait' }), 'cancel')
  assert.equal(availableJobAction({ ...baseJob, status: 'ready' }), null)
  assert.equal(availableJobAction({ ...baseJob, status: 'cancelled' }), null)
  assert.equal(availableJobAction({ ...baseJob, status: 'failed', retryable: false }), null)
  assert.equal(availableJobAction({ ...baseJob, status: 'failed', retryable: true }), 'retry')
})
