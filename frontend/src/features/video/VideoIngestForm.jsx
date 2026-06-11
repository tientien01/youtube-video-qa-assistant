import { useState } from 'react'

const INGEST_STEPS = [
  'Metadata',
  'Transcript',
  'Chunking',
  'Indexing',
]

export function VideoIngestForm({ onSubmit, isLoading, ingestStage }) {
  const [url, setUrl] = useState('')

  function handleSubmit(event) {
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

      {isLoading && ingestStage ? (
        <div className="ingest-progress" aria-live="polite">
          <p className="ingest-stage">{ingestStage}</p>
          <ol>
            {INGEST_STEPS.map((step) => (
              <li key={step}>{step}</li>
            ))}
          </ol>
        </div>
      ) : null}
    </form>
  )
}
