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
    onGenerate(formData.get('summary-mode'))
  }

  if (!video) {
    return (
      <section className="summary-panel" aria-label="Khu vực summary">
        <h2>Summary</h2>
        <p className="muted-text">Ingest một video trước khi tạo summary.</p>
      </section>
    )
  }

  return (
    <section className="summary-panel" aria-label="Khu vực summary">
      <div className="panel-heading">
        <h2>Summary</h2>
        <p className="muted-text">Tạo tóm tắt từ transcript đã ingest, có timestamp nguồn để kiểm chứng.</p>
      </div>

      <form className="summary-form" onSubmit={handleSubmit}>
        <label className="summary-mode-field" htmlFor="summary-mode">
          Chế độ
          <select id="summary-mode" name="summary-mode" disabled={isLoading}>
            <option value="short">Ngắn</option>
            <option value="detailed">Chi tiết</option>
            <option value="timeline">Timeline</option>
          </select>
        </label>
        <button type="submit" disabled={isLoading}>
          {isLoading ? 'Đang tạo...' : 'Tạo summary'}
        </button>
      </form>

      {error ? <p className="error-message">{error}</p> : null}

      {summary ? (
        <article className="summary-result">
          <div className="answer-heading">
            <p className="question-text">
              {summary.mode}
            </p>
            <span>{summary.cached ? 'cached' : 'new'}</span>
          </div>
          <p className="answer-text">{summary.summary}</p>

          {summary.sources.length > 0 ? (
            <div className="source-list">
              <h3>Nguồn transcript</h3>
              {summary.sources.map((source) => (
                <a
                  className="source-item"
                  href={buildYouTubeTimestampUrl(video.video_id, source.start_seconds)}
                  target="_blank"
                  rel="noreferrer"
                  key={source.chunk_id}
                >
                  <span>{formatTimestamp(source.start_seconds)}</span>
                  <span>{source.text}</span>
                </a>
              ))}
            </div>
          ) : null}
        </article>
      ) : (
        <p className="muted-text">Chưa có summary cho video này.</p>
      )}
    </section>
  )
}
