import { useState } from 'react'
import { buildYouTubeTimestampUrl, formatTimestamp } from '../../shared/utils/time'

export function RagDebugPanel({
  video,
  debugResult,
  onRetrieve,
  onAskInChat,
  isLoading,
  error,
}) {
  const [question, setQuestion] = useState('')
  const [retrievalMode, setRetrievalMode] = useState('hybrid')
  const [topK, setTopK] = useState(4)

  function handleSubmit(event) {
    event.preventDefault()
    const trimmedQuestion = question.trim()
    if (!trimmedQuestion) {
      return
    }

    onRetrieve({
      question: trimmedQuestion,
      retrievalMode,
      topK: Number(topK),
    })
  }

  if (!video) {
    return (
      <section className="debug-panel" aria-label="RAG debug">
        <h2>RAG Debug</h2>
        <p className="muted-text">Select an ingested video before inspecting retrieval.</p>
      </section>
    )
  }

  return (
    <section className="debug-panel" aria-label="RAG debug">
      <div className="panel-heading">
        <h2>RAG Debug</h2>
        <p className="muted-text">Inspect retrieved chunks, scores and latency for a question.</p>
      </div>

      <form className="debug-form" onSubmit={handleSubmit}>
        <label className="debug-question-field" htmlFor="debug-question">
          Debug question
          <textarea
            id="debug-question"
            name="debug-question"
            rows="3"
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
            placeholder="What concept does this video explain?"
            disabled={isLoading}
            required
          />
        </label>

        <div className="debug-options">
          <label className="debug-field" htmlFor="debug-retrieval-mode">
            Retrieval
            <select
              id="debug-retrieval-mode"
              value={retrievalMode}
              onChange={(event) => setRetrievalMode(event.target.value)}
              disabled={isLoading}
            >
              <option value="hybrid">Hybrid</option>
              <option value="embedding">Embedding</option>
              <option value="bm25">BM25</option>
            </select>
          </label>

          <label className="debug-field" htmlFor="debug-top-k">
            Top K
            <input
              id="debug-top-k"
              type="number"
              min="1"
              max="20"
              value={topK}
              onChange={(event) => setTopK(event.target.value)}
              disabled={isLoading}
              required
            />
          </label>

          <button type="submit" disabled={isLoading}>
            {isLoading ? 'Running...' : 'Run debug'}
          </button>
        </div>
      </form>

      {error ? <p className="error-message">{error}</p> : null}

      {debugResult ? (
        <article className="debug-result">
          <div className="answer-heading">
            <div>
              <p className="eyebrow">Debug query</p>
              <p className="question-text">{debugResult.question}</p>
            </div>
            <span>{debugResult.retrieval_mode}</span>
          </div>

          <dl className="debug-metrics">
            <div>
              <dt>Top K</dt>
              <dd>{debugResult.top_k}</dd>
            </div>
            <div>
              <dt>Latency</dt>
              <dd>{debugResult.latency_ms} ms</dd>
            </div>
            <div>
              <dt>Chunks</dt>
              <dd>{debugResult.chunks.length}</dd>
            </div>
          </dl>

          <div className="debug-actions">
            <button type="button" onClick={onAskInChat}>
              Ask in Chat with these chunks
            </button>
          </div>

          <div className="debug-chunk-list">
            {debugResult.chunks.length === 0 ? (
              <p className="muted-text">No chunks retrieved.</p>
            ) : (
              debugResult.chunks.map((chunk) => (
                <a
                  className="debug-chunk"
                  href={buildYouTubeTimestampUrl(video.video_id, chunk.start_seconds)}
                  target="_blank"
                  rel="noreferrer"
                  key={chunk.chunk_id}
                >
                  <span>{formatTimestamp(chunk.start_seconds)}</span>
                  <span>{chunk.score.toFixed(6)}</span>
                  <span>{chunk.text}</span>
                </a>
              ))
            )}
          </div>
        </article>
      ) : (
        <p className="muted-text">No debug result yet for this video.</p>
      )}
    </section>
  )
}
