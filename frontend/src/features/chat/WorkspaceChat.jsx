import { useState } from 'react'
import { formatTimestamp } from '../../shared/utils/time'

export function WorkspaceChat({ messages, isAsking, error, onAsk, onSelectSource, onClear }) {
  const [question, setQuestion] = useState('')
  function submit(event) {
    event.preventDefault()
    const value = question.trim()
    if (!value) return
    onAsk(value, 'hybrid')
    setQuestion('')
  }
  return (
    <section className="workspace-panel conversation-panel" aria-label="Ask this video">
      <header className="workspace-panel-header"><div><p className="panel-kicker">Grounded assistant</p><h2>Ask this video</h2></div>{messages.length ? <button className="text-button" type="button" onClick={onClear}>Clear</button> : null}</header>
      <div className="conversation-scroll">
        {!messages.length && !isAsking ? <div className="chat-empty"><span>✦</span><strong>Start with the source</strong><p>Ask about a concept, claim, or moment in this video.</p></div> : null}
        {messages.map((message) => (
          <article className="conversation-message" key={message.id}>
            <p className="user-bubble">{message.question}</p>
            <div className="assistant-answer"><p>{message.answer}</p>
              <div className="inline-citations">{message.sources.map((source) => <button type="button" key={source.chunk_id} onClick={() => onSelectSource(source)}>{formatTimestamp(source.start_seconds)}</button>)}</div>
              {message.generation?.fallback_reason ? <p className="provider-state">Provider unavailable: {message.generation.fallback_reason}</p> : null}
              {!message.sources.length ? <p className="insufficient-state">Insufficient transcript evidence.</p> : null}
            </div>
          </article>
        ))}
        {isAsking ? <p className="generating-state">Finding evidence and generating an answer…</p> : null}
        {error ? <p className="provider-state">{error}</p> : null}
      </div>
      <form className="workspace-composer" onSubmit={submit}>
        <label><span className="sr-only">Question</span><textarea rows="2" value={question} onChange={(event) => setQuestion(event.target.value)} placeholder="Ask a question grounded in this video…" disabled={isAsking} /></label>
        <button type="submit" disabled={isAsking || !question.trim()} aria-label="Send question">↑</button>
      </form>
    </section>
  )
}
