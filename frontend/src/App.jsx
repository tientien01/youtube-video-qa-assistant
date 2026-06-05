import { useEffect, useState } from 'react'
import './App.css'
import { askVideoQuestion } from './features/chat/chatApi'
import { ChatPanel } from './features/chat/ChatPanel'
import { deleteVideo, ingestVideo, listVideos } from './features/video/videoApi'
import { VideoHistory } from './features/video/VideoHistory'
import { VideoIngestForm } from './features/video/VideoIngestForm'
import { VideoResult } from './features/video/VideoResult'
import {
  mergeVideoHistory,
  readCurrentVideo,
  readVideoHistory,
  removeVideoFromStorage,
  saveCurrentVideo,
  saveVideoToHistory,
} from './features/video/videoStorage'

function App() {
  const [video, setVideo] = useState(() => readCurrentVideo())
  const [videoHistory, setVideoHistory] = useState(() => readVideoHistory())
  const [error, setError] = useState('')
  const [chatError, setChatError] = useState('')
  const [messages, setMessages] = useState([])
  const [isLoading, setIsLoading] = useState(false)
  const [isAsking, setIsAsking] = useState(false)
  const [isHistoryLoading, setIsHistoryLoading] = useState(false)

  useEffect(() => {
    let isActive = true

    async function loadVideoHistory() {
      setIsHistoryLoading(true)
      try {
        const backendVideos = await listVideos()
        if (!isActive) {
          return
        }

        setVideoHistory(mergeVideoHistory(backendVideos))
      } catch {
        if (isActive) {
          setVideoHistory(readVideoHistory())
        }
      } finally {
        if (isActive) {
          setIsHistoryLoading(false)
        }
      }
    }

    loadVideoHistory()

    return () => {
      isActive = false
    }
  }, [])

  async function handleIngest(url) {
    setIsLoading(true)
    setError('')
    setChatError('')
    setMessages([])

    try {
      const response = await ingestVideo(url)
      applySelectedVideo(response)
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

  function handleSelectVideo(nextVideo) {
    applySelectedVideo(nextVideo)
  }

  async function handleDeleteVideo(videoId) {
    setError('')
    setChatError('')

    try {
      await deleteVideo(videoId)
    } catch (requestError) {
      if (!requestError.message.includes('indexed')) {
        setError(requestError.message)
        return
      }
    }

    const nextHistory = removeVideoFromStorage(videoId)
    setVideoHistory(nextHistory)
    setMessages([])

    if (video?.video_id === videoId) {
      setVideo(null)
    }
  }

  function applySelectedVideo(nextVideo) {
    const normalizedVideo = normalizeVideo(nextVideo)
    setVideo(normalizedVideo)
    saveCurrentVideo(normalizedVideo)
    setVideoHistory(saveVideoToHistory(normalizedVideo))
    setMessages([])
    setChatError('')
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

        <VideoHistory
          videos={videoHistory}
          currentVideoId={video?.video_id}
          onSelect={handleSelectVideo}
          onDelete={handleDeleteVideo}
          isLoading={isHistoryLoading}
        />

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

function normalizeVideo(video) {
  return {
    ...video,
    status: video.status || 'cached',
    updated_at: video.updated_at || new Date().toISOString(),
  }
}

export default App
