export function RuntimeHealth({ health, error, compact = false }) {
  if (error) return <p className="runtime-unavailable">Health unavailable</p>
  if (!health) return <p className="runtime-pending">Checking runtime…</p>
  const components = [health.api, health.sqlite, health.vector_index, health.llm]
  return (
    <details className={`runtime-health ${compact ? 'compact' : ''}`}>
      <summary>
        <span className={`status-dot ${health.status}`} aria-hidden="true" />
        {health.status === 'operational' ? 'Operational' : 'Degraded'}
      </summary>
      <div className="runtime-health-list">
        {components.map((component) => (
          <div key={component.label}>
            <span className={`status-dot ${component.status}`} aria-hidden="true" />
            <span>{component.label}</span>
            <strong>{component.status}</strong>
          </div>
        ))}
      </div>
    </details>
  )
}

export function RuntimeCards({ health }) {
  return (
    <div className="runtime-cards">
      <article>
        <span className={`status-dot ${health?.llm.status || 'unavailable'}`} aria-hidden="true" />
        <div><small>LLM runtime</small><strong>{health ? `${health.llm.provider} / ${health.llm.model}` : 'Unavailable'}</strong></div>
      </article>
      <article>
        <span className={`status-dot ${health?.sqlite.status || 'unavailable'}`} aria-hidden="true" />
        <div><small>SQLite database</small><strong>{formatBytes(health?.database_size_bytes)}</strong></div>
      </article>
    </div>
  )
}

function formatBytes(value) {
  if (typeof value !== 'number') return 'Size unavailable'
  if (value < 1024 * 1024) return `${Math.max(1, Math.round(value / 1024))} KB`
  return `${(value / 1024 / 1024).toFixed(1)} MB`
}
