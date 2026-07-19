import { useEffect, useState } from 'react'

export function useRoute() {
  const [path, setPath] = useState(() => window.location.pathname)
  useEffect(() => {
    const update = () => setPath(window.location.pathname)
    window.addEventListener('popstate', update)
    return () => window.removeEventListener('popstate', update)
  }, [])

  function navigate(nextPath) {
    if (nextPath === window.location.pathname) return
    window.history.pushState({}, '', nextPath)
    setPath(nextPath)
  }

  return { path, navigate }
}

export function parseRoute(path) {
  const workspace = path.match(/^\/library\/([^/]+)$/)
  if (workspace) return { page: 'workspace', videoId: decodeURIComponent(workspace[1]) }
  const known = new Map([
    ['/', 'home'],
    ['/library', 'library'],
    ['/learning', 'learning'],
    ['/notes', 'notes'],
    ['/quizzes', 'quizzes'],
    ['/export', 'export'],
    ['/developer', 'developer'],
    ['/settings', 'settings'],
  ])
  return { page: known.get(path) || 'not-found', videoId: null }
}
