import {
  ArrowLeft,
  ArrowRight,
  Download,
  FileText,
  GraduationCap,
  House,
  Library,
  NotebookPen,
  Play,
} from 'lucide-react'
import { RuntimeCards, RuntimeHealth } from '../features/runtime-health/RuntimeHealth'

const NAVIGATION = [
  { id: 'home', label: 'Home', path: '/', Icon: House },
  { id: 'library', label: 'Library', path: '/library', Icon: Library },
  { id: 'learning', label: 'Summary', path: '/learning', Icon: FileText },
  { id: 'notes', label: 'Study Notes', path: '/notes', Icon: NotebookPen },
  { id: 'quizzes', label: 'Quizzes', path: '/quizzes', Icon: GraduationCap },
  { id: 'export', label: 'Export', path: '/export', Icon: Download },
]

export function ApplicationShell({ route, navigate, video, health, healthError, language, onLanguage, children }) {
  return (
    <div className="product-shell">
      <aside className="navigation-rail">
        <button className="product-mark" type="button" onClick={() => navigate('/')} aria-label="Go home">
          <span className="brand-icon" aria-hidden="true"><Play size={19} fill="currentColor" /></span>
          <div><strong>FrameNote</strong><small>Video learning</small></div>
        </button>
        <nav aria-label="Primary navigation">
          {NAVIGATION.map(({ id, label, path, Icon }) => (
            <button
              key={id}
              type="button"
              className={route.page === id || (id === 'library' && route.page === 'workspace') ? 'active' : ''}
              onClick={() => navigate(path)}
              title={label}
            >
              <Icon className="nav-icon" size={19} strokeWidth={1.8} aria-hidden="true" />
              <b>{label}</b>
            </button>
          ))}
        </nav>
        <RuntimeCards health={health} />
      </aside>
      <div className="shell-main">
        <header className="top-bar">
          <div className="history-controls">
            <button type="button" onClick={() => history.back()} aria-label="Go back" title="Go back">
              <ArrowLeft size={17} aria-hidden="true" />
            </button>
            <button type="button" onClick={() => history.forward()} aria-label="Go forward" title="Go forward">
              <ArrowRight size={17} aria-hidden="true" />
            </button>
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
