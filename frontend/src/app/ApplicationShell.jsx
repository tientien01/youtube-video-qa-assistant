import { RuntimeCards, RuntimeHealth } from '../features/runtime-health/RuntimeHealth'

const NAVIGATION = [
  ['home', 'Home', '/', '⌂', false],
  ['library', 'Library', '/library', '▤', false],
  ['learning', 'Learning', '/learning', '◇', false],
  ['notes', 'Notes', '/notes', '□', false],
  ['quizzes', 'Quizzes', '/quizzes', '✓', false],
  ['flashcards', 'Flashcards', '/flashcards', '▱', true],
  ['activity', 'Activity', '/activity', '◷', true],
  ['developer', 'Developer', '/developer', '⌘', false],
  ['settings', 'Settings', '/settings', '⚙', false],
]

export function ApplicationShell({ route, navigate, video, health, healthError, language, onLanguage, children }) {
  return (
    <div className="product-shell">
      <aside className="navigation-rail">
        <button className="product-mark" type="button" onClick={() => navigate('/')} aria-label="Go home">
          <span>▶</span><div><strong>FrameNote</strong><small>Video learning</small></div>
        </button>
        <nav aria-label="Primary navigation">
          {NAVIGATION.map(([id, label, path, icon, planned]) => (
            <button
              key={id}
              type="button"
              className={route.page === id || (id === 'library' && route.page === 'workspace') ? 'active' : ''}
              onClick={() => !planned && navigate(path)}
              disabled={planned}
              title={planned ? `${label} — Coming later` : label}
            >
              <span aria-hidden="true">{icon}</span><b>{label}</b>{planned ? <small>Later</small> : null}
            </button>
          ))}
        </nav>
        <RuntimeCards health={health} />
      </aside>
      <div className="shell-main">
        <header className="top-bar">
          <div className="history-controls">
            <button type="button" onClick={() => history.back()} aria-label="Go back">←</button>
            <button type="button" onClick={() => history.forward()} aria-label="Go forward">→</button>
          </div>
          <p className="breadcrumb"><span>Library</span>{video ? <> / <strong>{video.title}</strong></> : null}</p>
          <div className="command-unavailable" aria-label="Global search unavailable">Search unavailable <kbd>Ctrl K</kbd></div>
          <label className="language-switcher">Language
            <select value={language} onChange={(event) => onLanguage(event.target.value)}>
              <option value="vi">VI</option><option value="en">EN</option>
            </select>
          </label>
          <RuntimeHealth health={health} error={healthError} compact />
        </header>
        <main className="route-content">{children}</main>
      </div>
    </div>
  )
}
