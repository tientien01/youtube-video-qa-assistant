import { useState } from 'react'

export function VideoIngestForm({ onSubmit, isLoading }) {
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
          {isLoading ? 'Processing...' : 'Ingest Video'}
        </button>
      </div>
    </form>
  )
}
