import { useState } from 'react'
import type { FormEvent } from 'react'
import type { IngestJob } from './videoApi'
import { ACTIVE_INGEST_STATUSES, availableJobAction, STAGE_LABELS } from './ingestJobState'

interface Props {
  onSubmit: (url: string) => void
  onRetry: () => void
  onCancel: () => void
  ingestJob: IngestJob | null
}

export function VideoIngestForm({ onSubmit, onRetry, onCancel, ingestJob }: Props) {
  const [url, setUrl] = useState('')
  const jobAction = ingestJob ? availableJobAction(ingestJob) : null
  const isLoading = Boolean(ingestJob && ACTIVE_INGEST_STATUSES.has(ingestJob.status))

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()

    const trimmedUrl = url.trim()
    if (!trimmedUrl) {
      return
    }

    onSubmit(trimmedUrl)
  }

  return (
    <form className="ingest-form" onSubmit={handleSubmit}>
      <div className="panel-heading compact-heading">
        <p className="eyebrow">Video</p>
        <h2>Ingest a YouTube video</h2>
        <p className="muted-text">Paste a video URL to build transcript chunks and a local retrieval index.</p>
      </div>

      <label htmlFor="youtube-url">YouTube URL</label>
      <div className="form-row">
        <input
          id="youtube-url"
          name="youtube-url"
          type="url"
          value={url}
          onChange={(event) => setUrl(event.target.value)}
          placeholder="https://www.youtube.com/watch?v=dQw4w9WgXcQ"
          disabled={isLoading}
          required
        />
        <button type="submit" disabled={isLoading}>
          {isLoading ? 'Processing...' : 'Ingest'}
        </button>
      </div>

      {ingestJob ? (
        <div className={`ingest-progress ingest-${ingestJob.status}`} aria-live="polite">
          <p className="ingest-stage">{STAGE_LABELS[ingestJob.stage]}</p>
          <p className="muted-text">State: {ingestJob.status.replace('_', ' ')}</p>
          {ingestJob.error ? <p className="error-message">{ingestJob.error.message}</p> : null}
          {jobAction === 'cancel' ? <button type="button" onClick={onCancel}>Cancel</button> : null}
          {jobAction === 'retry' ? (
            <button type="button" onClick={onRetry}>Retry</button>
          ) : null}
        </div>
      ) : null}
    </form>
  )
}
