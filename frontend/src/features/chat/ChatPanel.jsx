import { useState } from 'react'
import { buildYouTubeTimestampUrl, formatTimestamp } from '../../shared/utils/time'

export function ChatPanel({
  video,
  messages,
  onAsk,
  onRegenerate,
  onAskWithSource,
  onToggleExport,
  onClearHistory,
  isAsking,
  error,
}) {
  const [question, setQuestion] = useState('')
  const [retrievalMode, setRetrievalMode] = useState('hybrid')

  function handleSubmit(event) {
    event.preventDefault()

    const trimmedQuestion = question.trim()
    if (!trimmedQuestion) {
      return
    }

    onAsk(trimmedQuestion, retrievalMode)
    setQuestion('')
  }

  if (!video) {
    return (
      <section className="chat-panel" aria-label="Chat">
        <EmptyPanel title="Chat" message="Select an ingested video before asking questions." />
      </section>
    )
  }

  return (
    <section className="chat-panel" aria-label="Chat">
      <div className="panel-heading split-heading">
        <div>
          <h2>Chat with transcript</h2>
          <p className="muted-text">Answers stay grounded in retrieved transcript chunks.</p>
        </div>
        {messages.length > 0 ? (
          <button className="secondary-button" type="button" onClick={onClearHistory}>
            Clear history
          </button>
        ) : null}
      </div>

      <form className="question-form" onSubmit={handleSubmit}>
        <label className="question-field" htmlFor="question">
          Question
          <textarea
            id="question"
            name="question"
            rows="3"
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
            placeholder="What are the key ideas in this video?"
            disabled={isAsking}
            required
          />
        </label>

        <div className="form-actions-row">
          <label className="retrieval-mode-field" htmlFor="retrieval-mode">
            Retrieval
            <select
              id="retrieval-mode"
              value={retrievalMode}
              onChange={(event) => setRetrievalMode(event.target.value)}
              disabled={isAsking}
            >
              <option value="hybrid">Hybrid</option>
              <option value="embedding">Embedding</option>
              <option value="bm25">BM25</option>
            </select>
          </label>
          <button type="submit" disabled={isAsking}>
            {isAsking ? 'Answering...' : 'Ask'}
          </button>
        </div>
      </form>

      {error ? <p className="error-message">{error}</p> : null}

      <div className="message-list">
        {messages.length === 0 ? (
          <p className="muted-text">No questions yet for this video.</p>
        ) : (
          messages.map((message) => (
            <article className="answer-card" key={message.id}>
              <div className="answer-heading">
                <div>
                  <p className="eyebrow">Question</p>
                  <p className="question-text">{message.question}</p>
                </div>
                <div className="status-tags">
                  <span>{message.retrievalMode || 'hybrid'}</span>
                  {message.generation ? <span>{formatGeneration(message.generation)}</span> : null}
                </div>
              </div>

              <p className="answer-text">{message.answer}</p>

              <div className="chat-message-actions">
                <label className="export-message-toggle">
                  <input
                    type="checkbox"
                    checked={Boolean(message.selectedForExport)}
                    onChange={() => onToggleExport(message.id)}
                  />
                  <span>Include in export</span>
                </label>
                <button type="button" onClick={() => onRegenerate(message)} disabled={isAsking}>
                  Regenerate
                </button>
              </div>

              {message.groundednessWarning ? (
                <p className="warning-message">{message.groundednessWarning}</p>
              ) : null}
              {message.generation?.fallback_reason ? (
                <p className="muted-text">Fallback: {message.generation.fallback_reason}</p>
              ) : null}

              {message.sources.length > 0 ? (
                <SourceList
                  videoId={video.video_id}
                  sources={message.sources}
                  actionLabel="Ask with this source"
                  onAction={(source) => onAskWithSource(message, source)}
                  disabled={isAsking}
                />
              ) : null}
            </article>
          ))
        )}
      </div>
    </section>
  )
}

function EmptyPanel({ title, message }) {
  return (
    <>
      <h2>{title}</h2>
      <p className="muted-text">{message}</p>
    </>
  )
}

function SourceList({ videoId, sources, actionLabel, onAction, disabled }) {
  return (
    <div className="source-list">
      <h3>Transcript sources</h3>
      {sources.map((source) => (
        <div className="source-item source-item-with-action" key={source.chunk_id}>
          <a
            href={buildYouTubeTimestampUrl(videoId, source.start_seconds)}
            target="_blank"
            rel="noreferrer"
          >
            {formatTimestamp(source.start_seconds)}
          </a>
          <span>{source.text}</span>
          <button type="button" onClick={() => onAction(source)} disabled={disabled}>
            {actionLabel}
          </button>
        </div>
      ))}
    </div>
  )
}

function formatGeneration(generation) {
  return `${generation.generation_mode}:${generation.provider}`
}
