import type { IngestJob } from './videoApi'

export const ACTIVE_INGEST_STATUSES = new Set<IngestJob['status']>(['pending', 'running', 'retry_wait'])

export const STAGE_LABELS: Record<IngestJob['stage'], string> = {
  pending: 'Waiting to start',
  fetching_metadata: 'Fetching video metadata',
  fetching_transcript: 'Fetching transcript',
  normalizing: 'Normalizing transcript',
  validating: 'Validating transcript',
  chunking: 'Building transcript chunks',
  embedding: 'Creating embeddings',
  committing: 'Publishing the index',
  complete: 'Ready',
}

export function availableJobAction(job: IngestJob): 'cancel' | 'retry' | null {
  if (ACTIVE_INGEST_STATUSES.has(job.status)) return 'cancel'
  if (job.status === 'failed' && job.retryable) return 'retry'
  return null
}
