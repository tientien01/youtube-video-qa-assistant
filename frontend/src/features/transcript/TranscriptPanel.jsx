import { useMemo, useState } from 'react'
import { Play } from 'lucide-react'
import { formatTimestamp } from '../../shared/utils/time'

export function TranscriptPanel({ transcript, loading, error, currentTime, selectedSource, onSeek }) {
  const [search, setSearch] = useState('')
  const filtered = useMemo(() => {
    if (!transcript) return []
    const query = search.trim().toLocaleLowerCase()
    return query ? transcript.segments.filter((item) => item.original_text.toLocaleLowerCase().includes(query)) : transcript.segments
  }, [search, transcript])

  return (
    <section className="workspace-panel transcript-panel" aria-label="Transcript">
      <header className="workspace-panel-header">
        <div><p className="panel-kicker">Source</p><h2>Transcript</h2></div>
        <span className="language-badge">{transcript?.language_code?.toUpperCase() || '—'}</span>
        <label className="transcript-search"><span className="sr-only">Search transcript</span>
          <input type="search" value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search transcript" />
        </label>
      </header>
      <div className="transcript-scroll" aria-live="polite">
        {loading ? <PanelState title="Loading transcript…" /> : null}
        {error ? <PanelState title="Transcript unavailable" detail={error} danger /> : null}
        {!loading && !error && transcript && filtered.length === 0 ? <PanelState title="No transcript matches" /> : null}
        {filtered.map((segment) => {
          const active = currentTime >= segment.start_seconds && currentTime < segment.end_seconds
          const selected = selectedSource && rangesOverlap(segment, selectedSource)
          return (
            <button
              type="button"
              className={`transcript-row ${active ? 'active' : ''} ${selected ? 'selected' : ''}`}
              key={segment.segment_id}
              onClick={() => onSeek(segment.start_seconds, segment)}
            >
              <time>{formatTimestamp(segment.start_seconds)}</time>
              <span>{segment.original_text}</span>
              {active ? <Play className="transcript-play-icon" size={14} fill="currentColor" role="img" aria-label="Currently playing" /> : null}
            </button>
          )
        })}
      </div>
    </section>
  )
}

function rangesOverlap(segment, source) {
  return segment.start_seconds < source.end_seconds && segment.end_seconds > source.start_seconds
}

function PanelState({ title, detail, danger }) {
  return <div className={`panel-state ${danger ? 'danger' : ''}`}><strong>{title}</strong>{detail ? <p>{detail}</p> : null}</div>
}
