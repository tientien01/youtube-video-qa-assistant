import { buildYouTubeTimestampUrl, formatTimestamp } from '../../shared/utils/time'

export function NotesPanel({
  video,
  notes,
  onGenerate,
  isLoading,
  error,
}) {
  function handleSubmit(event) {
    event.preventDefault()
    const formData = new FormData(event.currentTarget)
    onGenerate({
      mode: formData.get('notes-mode'),
      learningGoal: formData.get('learning-goal').trim(),
      force: false,
    })
  }

  function handleRegenerate(event) {
    const form = event.currentTarget.form
    if (!form) {
      return
    }

    const formData = new FormData(form)
    onGenerate({
      mode: formData.get('notes-mode'),
      learningGoal: formData.get('learning-goal').trim(),
      force: true,
    })
  }

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

      <form className="notes-form" onSubmit={handleSubmit}>
        <label className="notes-field" htmlFor="notes-mode">
          Chế độ
          <select id="notes-mode" name="notes-mode" disabled={isLoading} defaultValue={notes?.mode || 'concise'}>
            <option value="concise">Ngắn gọn</option>
            <option value="detailed">Chi tiết</option>
            <option value="timeline">Timeline</option>
            <option value="exam_review">Ôn thi</option>
            <option value="beginner">Dễ hiểu</option>
          </select>
        </label>
        <label className="notes-field notes-goal-field" htmlFor="learning-goal">
          Mục tiêu học
          <input
            id="learning-goal"
            name="learning-goal"
            type="text"
            defaultValue={notes?.learning_goal || ''}
            placeholder="Ví dụ: ôn thi, hiểu khái niệm chính"
            disabled={isLoading}
          />
        </label>
        <div className="notes-actions">
          <button type="submit" disabled={isLoading}>
            {isLoading ? 'Đang tạo...' : 'Tạo study notes'}
          </button>
          <button type="button" onClick={handleRegenerate} disabled={isLoading}>
            Tạo lại
          </button>
        </div>
      </form>

      {error ? <p className="error-message">{error}</p> : null}

      {notes ? (
        <article className="notes-result">
          <div className="answer-heading">
            <p className="question-text">Study notes {notes.mode ? `(${formatMode(notes.mode)})` : ''}</p>
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
                  <span>
                    {formatTimestamp(source.start_seconds)}
                    {'-'}
                    {formatTimestamp(source.end_seconds)}
                  </span>
                  <span>{buildSourceExcerpt(source.text)}</span>
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

function formatMode(mode) {
  const labels = {
    concise: 'ngắn gọn',
    detailed: 'chi tiết',
    timeline: 'timeline',
    exam_review: 'ôn thi',
    beginner: 'dễ hiểu',
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
