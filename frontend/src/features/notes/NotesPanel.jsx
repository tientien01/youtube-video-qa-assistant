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
      length: formData.get('notes-length'),
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
      length: formData.get('notes-length'),
      learningGoal: formData.get('learning-goal').trim(),
      force: true,
    })
  }

  if (!video) {
    return (
      <section className="notes-panel" aria-label="Study notes">
        <h2>Study Notes</h2>
        <p className="muted-text">Select an ingested video before generating notes.</p>
      </section>
    )
  }

  return (
    <section className="notes-panel" aria-label="Study notes">
      <div className="panel-heading">
        <h2>Study Notes</h2>
        <p className="muted-text">Create review material from transcript sources.</p>
      </div>

      <form className="notes-form" onSubmit={handleSubmit}>
        <label className="notes-field" htmlFor="notes-mode">
          Mode
          <select id="notes-mode" name="notes-mode" disabled={isLoading} defaultValue={notes?.mode || 'concise'}>
            <option value="concise">Concise</option>
            <option value="detailed">Detailed</option>
            <option value="timeline">Timeline</option>
            <option value="exam_review">Exam review</option>
            <option value="beginner">Beginner</option>
            <option value="flashcards">Flashcards</option>
            <option value="concept_map">Concept map</option>
          </select>
        </label>
        <label className="notes-field" htmlFor="notes-length">
          Length
          <select id="notes-length" name="notes-length" disabled={isLoading} defaultValue={notes?.length || 'medium'}>
            <option value="short">Short</option>
            <option value="medium">Medium</option>
            <option value="long">Long</option>
          </select>
        </label>
        <label className="notes-field notes-goal-field" htmlFor="learning-goal">
          Learning goal
          <input
            id="learning-goal"
            name="learning-goal"
            type="text"
            defaultValue={notes?.learning_goal || ''}
            placeholder="Exam review, core concepts, quick recap"
            disabled={isLoading}
          />
        </label>
        <div className="notes-actions">
          <button type="submit" disabled={isLoading}>
            {isLoading ? 'Generating...' : 'Generate'}
          </button>
          <button type="button" onClick={handleRegenerate} disabled={isLoading}>
            Regenerate
          </button>
        </div>
      </form>

      {error ? <p className="error-message">{error}</p> : null}

      {notes ? (
        <article className="notes-result">
          <div className="answer-heading">
            <div>
              <p className="eyebrow">Notes mode</p>
              <p className="question-text">
                {formatMode(notes.mode)}
                {notes.length ? ` | ${notes.length}` : ''}
              </p>
            </div>
            <div className="status-tags">
              <span>{notes.cached ? 'cached' : 'new'}</span>
              {notes.generation ? <span>{formatGeneration(notes.generation)}</span> : null}
            </div>
          </div>
          <div className="prose-output">{notes.notes}</div>
          {notes.generation?.fallback_reason ? (
            <p className="warning-message">{notes.generation.fallback_reason}</p>
          ) : null}

          {notes.sources.length > 0 ? (
            <SourceList videoId={video.video_id} sources={notes.sources} />
          ) : null}
        </article>
      ) : (
        <p className="muted-text">No study notes yet for this video.</p>
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
    concise: 'Concise',
    detailed: 'Detailed',
    timeline: 'Timeline',
    exam_review: 'Exam review',
    beginner: 'Beginner',
    flashcards: 'Flashcards',
    concept_map: 'Concept map',
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
