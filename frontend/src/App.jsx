import { useState } from 'react'
import './App.css'
import { ingestVideo } from './features/video/videoApi'
import { VideoIngestForm } from './features/video/VideoIngestForm'
import { VideoResult } from './features/video/VideoResult'

function App() {
  const [video, setVideo] = useState(null)
  const [error, setError] = useState('')
  const [isLoading, setIsLoading] = useState(false)

  async function handleIngest(url) {
    setIsLoading(true)
    setError('')
    setVideo(null)

    try {
      const response = await ingestVideo(url)
      setVideo(response)
    } catch (requestError) {
      setError(requestError.message)
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <main className="app-shell">
      <section className="intro-section">
        <p className="eyebrow">YouTube Video Q&A Assistant</p>
        <h1>Index a YouTube video before asking questions.</h1>
        <p className="intro-copy">
          Enter a YouTube URL to test the backend ingest contract. The current
          backend response is still mocked, but this screen is ready for the
          transcript and RAG steps that come next.
        </p>
      </section>

      <section className="workspace" aria-label="Video ingest workspace">
        <VideoIngestForm onSubmit={handleIngest} isLoading={isLoading} />

        {error ? <p className="error-message">{error}</p> : null}

        <VideoResult video={video} />
      </section>
    </main>
  )
}

export default App
