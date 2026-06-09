import { buildYouTubeTimestampUrl, formatTimestamp } from '../../shared/utils/time'

export function NotesPanel({
  video,
  notes,
  onGenerate,
  isLoading,
  error,
}) {
  if (!video) {
    return (
      <section className="notes-panel" aria-label="Khu vực study notes">
        <h2>Study Notes</h2>
        <p className="muted-text">Ingest một video trước khi tạo study notes.</p>
      </section>
    )
  }

  return (
    <section className="notes-panel" aria-label="Khu vực study notes">
      <div className="panel-heading">
        <h2>Study Notes</h2>
        <p className="muted-text">Tạo ghi chú học tập từ transcript đã ingest, có timestamp để xem lại.</p>
      </div>

      <button className="notes-action" type="button" onClick={onGenerate} disabled={isLoading}>
        {isLoading ? 'Đang tạo...' : 'Tạo study notes'}
      </button>

      {error ? <p className="error-message">{error}</p> : null}

      {notes ? (
        <article className="notes-result">
          <div className="answer-heading">
            <p className="question-text">Study notes</p>
            <div className="status-tags">
              <span>{notes.cached ? 'cached' : 'new'}</span>
              {notes.generation ? <span>{formatGeneration(notes.generation)}</span> : null}
            </div>
          </div>
          <p className="answer-text">{notes.notes}</p>
          {notes.generation?.fallback_reason ? (
            <p className="muted-text">Fallback: {notes.generation.fallback_reason}</p>
          ) : null}

          {notes.sources.length > 0 ? (
            <div className="source-list">
              <h3>Nguồn transcript</h3>
              {notes.sources.map((source) => (
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
        <p className="muted-text">Chưa có study notes cho video này.</p>
      )}
    </section>
  )
}

function formatGeneration(generation) {
  return `${generation.generation_mode}:${generation.provider}`
}
