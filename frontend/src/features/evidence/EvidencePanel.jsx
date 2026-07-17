import { formatTimestamp } from '../../shared/utils/time'

export function EvidencePanel({ sources, selectedSource, onSelect }) {
  return (
    <section className="workspace-panel evidence-panel" aria-label="Evidence">
      <header className="workspace-panel-header"><div><p className="panel-kicker">Grounding</p><h2>Evidence</h2></div><span>{sources.length} sources</span></header>
      <div className="evidence-scroll">
        {sources.length === 0 ? <div className="panel-state"><strong>No evidence yet</strong><p>Ask a question to retrieve timestamped sources.</p></div> : null}
        {sources.map((source, index) => (
          <article className={`evidence-card ${selectedSource?.chunk_id === source.chunk_id ? 'selected' : ''}`} key={source.chunk_id}>
            <div className="evidence-marker">{index + 1}</div>
            <div><button className="timestamp-link" type="button" onClick={() => onSelect(source, 'play')}>{formatTimestamp(source.start_seconds)}–{formatTimestamp(source.end_seconds)}</button><p>{source.text}</p>
              <div className="evidence-actions"><button type="button" onClick={() => onSelect(source, 'play')}>Play segment</button><button type="button" onClick={() => onSelect(source, 'transcript')}>View transcript</button></div>
            </div>
          </article>
        ))}
      </div>
    </section>
  )
}
