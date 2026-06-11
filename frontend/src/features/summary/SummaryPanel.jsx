import { buildYouTubeTimestampUrl, formatTimestamp } from '../../shared/utils/time'

export function SummaryPanel({
  video,
  summary,
  onGenerate,
  isLoading,
  error,
}) {
  function handleSubmit(event) {
    event.preventDefault()
    const formData = new FormData(event.currentTarget)
    onGenerate({ mode: formData.get('summary-mode'), force: false })
  }

  function handleRegenerate(event) {
    const form = event.currentTarget.form
    if (!form) {
      return
    }

    const formData = new FormData(form)
    onGenerate({ mode: formData.get('summary-mode'), force: true })
  }

  if (!video) {
    return (
      <section className="summary-panel" aria-label="Summary">
        <h2>Summary</h2>
        <p className="muted-text">Select an ingested video before generating a summary.</p>
      </section>
    )
  }

  return (
    <section className="summary-panel" aria-label="Summary">
      <div className="panel-heading">
        <h2>Summary</h2>
        <p className="muted-text">Generate a timestamped overview from the indexed transcript.</p>
      </div>

      <form className="summary-form" onSubmit={handleSubmit}>
        <label className="summary-mode-field" htmlFor="summary-mode">
          Mode
          <select id="summary-mode" name="summary-mode" disabled={isLoading} defaultValue={summary?.mode || 'short'}>
            <option value="short">Short</option>
            <option value="detailed">Detailed</option>
            <option value="timeline">Timeline</option>
          </select>
        </label>
        <button type="submit" disabled={isLoading}>
          {isLoading ? 'Generating...' : 'Generate'}
        </button>
        <button type="button" onClick={handleRegenerate} disabled={isLoading}>
          Regenerate
        </button>
      </form>

      {error ? <p className="error-message">{error}</p> : null}

      {summary ? (
        <article className="summary-result">
          <div className="answer-heading">
            <div>
              <p className="eyebrow">Summary mode</p>
              <p className="question-text">{formatMode(summary.mode)}</p>
            </div>
            <div className="status-tags">
              <span>{summary.cached ? 'cached' : 'new'}</span>
              {summary.generation ? <span>{formatGeneration(summary.generation)}</span> : null}
            </div>
          </div>
          <div className="prose-output">{summary.summary}</div>
          {summary.generation?.fallback_reason ? (
            <p className="warning-message">{summary.generation.fallback_reason}</p>
          ) : null}

          {summary.sources.length > 0 ? (
            <SourceList videoId={video.video_id} sources={summary.sources} />
          ) : null}
        </article>
      ) : (
        <p className="muted-text">No summary yet for this video.</p>
      )}
    </section>
  )
}

function SourceList({ videoId, sources }) {
  return (
    <div className="source-list">
      <h3>Transcript sources</h3>
      {sources.map((source) => (
        <a
          className="source-item"
          href={buildYouTubeTimestampUrl(videoId, source.start_seconds)}
          target="_blank"
          rel="noreferrer"
          key={source.chunk_id}
        >
          <span>
            {formatTimestamp(source.start_seconds)}
            {' - '}
            {formatTimestamp(source.end_seconds)}
          </span>
          <span>{buildSourceExcerpt(source.text)}</span>
        </a>
      ))}
    </div>
  )
}

function formatGeneration(generation) {
  return `${generation.generation_mode}:${generation.provider}`
}

function formatMode(mode) {
  const labels = {
    short: 'Short',
    detailed: 'Detailed',
    timeline: 'Timeline',
  }

  return labels[mode] || mode
}

function buildSourceExcerpt(text) {
  const normalizedText = text.replace(/\s+/g, ' ').trim()
  if (normalizedText.length <= 220) {
    return normalizedText
  }

  return `${normalizedText.slice(0, 217).trim()}...`
}
