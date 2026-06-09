import { useEffect, useState } from 'react'
import './App.css'
import { askVideoQuestion } from './features/chat/chatApi'
import { ChatPanel } from './features/chat/ChatPanel'
import { retrieveDebugContext } from './features/debug/debugApi'
import { RagDebugPanel } from './features/debug/RagDebugPanel'
import { ExportPanel } from './features/export/ExportPanel'
import { generateStudyNotes } from './features/notes/notesApi'
import { NotesPanel } from './features/notes/NotesPanel'
import { generateVideoQuiz } from './features/quiz/quizApi'
import { QuizPanel } from './features/quiz/QuizPanel'
import { generateVideoSummary } from './features/summary/summaryApi'
import { SummaryPanel } from './features/summary/SummaryPanel'
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
  const [summaryError, setSummaryError] = useState('')
  const [notesError, setNotesError] = useState('')
  const [quizError, setQuizError] = useState('')
  const [debugError, setDebugError] = useState('')
  const [messages, setMessages] = useState([])
  const [summary, setSummary] = useState(null)
  const [notes, setNotes] = useState(null)
  const [quiz, setQuiz] = useState(null)
  const [debugResult, setDebugResult] = useState(null)
  const [isLoading, setIsLoading] = useState(false)
  const [isAsking, setIsAsking] = useState(false)
  const [isSummaryLoading, setIsSummaryLoading] = useState(false)
  const [isNotesLoading, setIsNotesLoading] = useState(false)
  const [isQuizLoading, setIsQuizLoading] = useState(false)
  const [isDebugLoading, setIsDebugLoading] = useState(false)
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
    setSummaryError('')
    setNotesError('')
    setQuizError('')
    setDebugError('')
    setMessages([])
    setSummary(null)
    setNotes(null)
    setQuiz(null)
    setDebugResult(null)

    try {
      const response = await ingestVideo(url)
      applySelectedVideo(response)
    } catch (requestError) {
      setError(requestError.message)
    } finally {
      setIsLoading(false)
    }
  }

  async function handleAsk(question, retrievalMode) {
    if (!video) {
      return
    }

    setIsAsking(true)
    setChatError('')

    try {
      const response = await askVideoQuestion({
        videoId: video.video_id,
        question,
        retrievalMode,
      })
      setMessages((currentMessages) => [
        {
          id: `${Date.now()}-${currentMessages.length}`,
          question,
          answer: response.answer,
          retrievalMode: response.retrieval_mode,
          generation: response.generation,
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

  async function handleGenerateSummary(mode) {
    if (!video) {
      return
    }

    setIsSummaryLoading(true)
    setSummaryError('')

    try {
      const response = await generateVideoSummary({
        videoId: video.video_id,
        mode,
      })
      setSummary(response)
    } catch (requestError) {
      setSummaryError(requestError.message)
    } finally {
      setIsSummaryLoading(false)
    }
  }

  async function handleGenerateNotes() {
    if (!video) {
      return
    }

    setIsNotesLoading(true)
    setNotesError('')

    try {
      const response = await generateStudyNotes({
        videoId: video.video_id,
      })
      setNotes(response)
    } catch (requestError) {
      setNotesError(requestError.message)
    } finally {
      setIsNotesLoading(false)
    }
  }

  async function handleGenerateQuiz({ questionCount, difficulty, questionType }) {
    if (!video) {
      return
    }

    setIsQuizLoading(true)
    setQuizError('')

    try {
      const response = await generateVideoQuiz({
        videoId: video.video_id,
        questionCount,
        difficulty,
        questionType,
      })
      setQuiz(response)
    } catch (requestError) {
      setQuizError(requestError.message)
    } finally {
      setIsQuizLoading(false)
    }
  }

  async function handleDebugRetrieve({ question, retrievalMode, topK }) {
    if (!video) {
      return
    }

    setIsDebugLoading(true)
    setDebugError('')

    try {
      const response = await retrieveDebugContext({
        videoId: video.video_id,
        question,
        retrievalMode,
        topK,
      })
      setDebugResult(response)
    } catch (requestError) {
      setDebugError(requestError.message)
    } finally {
      setIsDebugLoading(false)
    }
  }

  function handleSelectVideo(nextVideo) {
    applySelectedVideo(nextVideo)
  }

  async function handleDeleteVideo(videoId) {
    setError('')
    setChatError('')
    setSummaryError('')
    setNotesError('')
    setQuizError('')
    setDebugError('')

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
      setSummary(null)
      setNotes(null)
      setQuiz(null)
      setDebugResult(null)
    }
  }

  function applySelectedVideo(nextVideo) {
    const normalizedVideo = normalizeVideo(nextVideo)
    setVideo(normalizedVideo)
    saveCurrentVideo(normalizedVideo)
    setVideoHistory(saveVideoToHistory(normalizedVideo))
    setMessages([])
    setSummary(null)
    setNotes(null)
    setQuiz(null)
    setDebugResult(null)
    setChatError('')
    setSummaryError('')
    setNotesError('')
    setQuizError('')
    setDebugError('')
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

        <SummaryPanel
          video={video}
          summary={summary}
          onGenerate={handleGenerateSummary}
          isLoading={isSummaryLoading}
          error={summaryError}
        />

        <NotesPanel
          video={video}
          notes={notes}
          onGenerate={handleGenerateNotes}
          isLoading={isNotesLoading}
          error={notesError}
        />

        <QuizPanel
          video={video}
          quiz={quiz}
          onGenerate={handleGenerateQuiz}
          isLoading={isQuizLoading}
          error={quizError}
        />

        <ExportPanel video={video} summary={summary} notes={notes} quiz={quiz} />

        <RagDebugPanel
          video={video}
          debugResult={debugResult}
          onRetrieve={handleDebugRetrieve}
          isLoading={isDebugLoading}
          error={debugError}
        />

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
