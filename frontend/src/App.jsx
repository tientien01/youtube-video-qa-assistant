import { useState } from 'react'
import './App.css'
import { askVideoQuestion } from './features/chat/chatApi'
import { ChatPanel } from './features/chat/ChatPanel'
import { ingestVideo } from './features/video/videoApi'
import { VideoIngestForm } from './features/video/VideoIngestForm'
import { VideoResult } from './features/video/VideoResult'

function App() {
  const [video, setVideo] = useState(null)
  const [error, setError] = useState('')
  const [chatError, setChatError] = useState('')
  const [messages, setMessages] = useState([])
  const [isLoading, setIsLoading] = useState(false)
  const [isAsking, setIsAsking] = useState(false)

  async function handleIngest(url) {
    setIsLoading(true)
    setError('')
    setChatError('')
    setVideo(null)
    setMessages([])

    try {
      const response = await ingestVideo(url)
      setVideo(response)
    } catch (requestError) {
      setError(requestError.message)
    } finally {
      setIsLoading(false)
    }
  }

  async function handleAsk(question) {
    if (!video) {
      return
    }

    setIsAsking(true)
    setChatError('')

    try {
      const response = await askVideoQuestion({
        videoId: video.video_id,
        question,
      })
      setMessages((currentMessages) => [
        {
          id: `${Date.now()}-${currentMessages.length}`,
          question,
          answer: response.answer,
          sources: response.sources,
        },
        ...currentMessages,
      ])
    } catch (requestError) {
      setChatError(requestError.message)
    } finally {
      setIsAsking(false)
    }
  }

  return (
    <main className="app-shell">
      <section className="intro-section">
        <p className="eyebrow">YouTube Video Q&A Assistant</p>
        <h1>Hỏi đáp theo nội dung transcript của video YouTube.</h1>
        <p className="intro-copy">
          Nhập URL YouTube, hệ thống sẽ lấy transcript, chia chunk, tạo index
          local và trả lời câu hỏi kèm timestamp tham chiếu.
        </p>
      </section>

      <section className="workspace" aria-label="Video ingest workspace">
        <VideoIngestForm onSubmit={handleIngest} isLoading={isLoading} />

        {error ? <p className="error-message">{error}</p> : null}

        <VideoResult video={video} />

        <ChatPanel
          video={video}
          messages={messages}
          onAsk={handleAsk}
          isAsking={isAsking}
          error={chatError}
        />
      </section>
    </main>
  )
}

export default App
