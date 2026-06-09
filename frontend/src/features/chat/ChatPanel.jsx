import { useState } from 'react'
import { buildYouTubeTimestampUrl, formatTimestamp } from '../../shared/utils/time'

export function ChatPanel({
  video,
  messages,
  onAsk,
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
      <section className="chat-panel" aria-label="Khu vực hỏi đáp">
        <h2>Hỏi đáp</h2>
        <p className="muted-text">Ingest một video trước khi đặt câu hỏi.</p>
      </section>
    )
  }

  return (
    <section className="chat-panel" aria-label="Khu vực hỏi đáp">
      <div className="panel-heading">
        <h2>Hỏi đáp theo transcript</h2>
        <p className="muted-text">Câu trả lời được tạo từ những đoạn transcript liên quan nhất.</p>
      </div>

      <form className="question-form" onSubmit={handleSubmit}>
        <div className="question-options">
          <label htmlFor="question">Câu hỏi</label>
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
        </div>
        <textarea
          id="question"
          name="question"
          rows="3"
          value={question}
          onChange={(event) => setQuestion(event.target.value)}
          placeholder="Video này giải thích nội dung chính là gì?"
          disabled={isAsking}
          required
        />
        <button type="submit" disabled={isAsking}>
          {isAsking ? 'Đang trả lời...' : 'Gửi câu hỏi'}
        </button>
      </form>

      {error ? <p className="error-message">{error}</p> : null}

      <div className="message-list">
        {messages.length === 0 ? (
          <p className="muted-text">Chưa có câu hỏi nào cho video này.</p>
        ) : (
          messages.map((message) => (
            <article className="answer-card" key={message.id}>
              <div className="answer-heading">
                <p className="question-text">{message.question}</p>
                <div className="status-tags">
                  <span>{message.retrievalMode || 'hybrid'}</span>
                  {message.generation ? <span>{formatGeneration(message.generation)}</span> : null}
                </div>
              </div>
              <p className="answer-text">{message.answer}</p>
              {message.generation?.fallback_reason ? (
                <p className="muted-text">Fallback: {message.generation.fallback_reason}</p>
              ) : null}

              {message.sources.length > 0 ? (
                <div className="source-list">
                  <h3>Nguồn transcript</h3>
                  {message.sources.map((source) => (
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
          ))
        )}
      </div>
    </section>
  )
}

function formatGeneration(generation) {
  return `${generation.generation_mode}:${generation.provider}`
}
