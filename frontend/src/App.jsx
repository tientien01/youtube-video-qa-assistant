import { useEffect, useState } from 'react'
import './App.css'
import { askVideoQuestion, clearBackendChatHistory, getChatHistory } from './features/chat/chatApi'
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
import { deleteVideo, ingestVideo, listVideos, rebuildVideoIndex } from './features/video/videoApi'
import { VideoHistory } from './features/video/VideoHistory'
import { VideoIngestForm } from './features/video/VideoIngestForm'
import { VideoResult } from './features/video/VideoResult'
import {
  mergeVideoHistory,
  readCurrentVideo,
  readVideoChatHistory,
  readVideoHistory,
  removeVideoFromStorage,
  saveCurrentVideo,
  saveVideoChatHistory,
  saveVideoToHistory,
} from './features/video/videoStorage'

const WORKSPACE_TABS = [
  { id: 'chat', label: 'Chat' },
  { id: 'summary', label: 'Summary' },
  { id: 'notes', label: 'Notes' },
  { id: 'quiz', label: 'Quiz' },
  { id: 'export', label: 'Export' },
  { id: 'debug', label: 'Debug' },
]
const ACTIVE_TAB_KEY = 'youtube-qa-active-workspace-tab'

function App() {
  const [video, setVideo] = useState(() => readCurrentVideo())
  const [videoHistory, setVideoHistory] = useState(() => readVideoHistory())
  const [error, setError] = useState('')
  const [chatError, setChatError] = useState('')
  const [summaryError, setSummaryError] = useState('')
  const [notesError, setNotesError] = useState('')
  const [quizError, setQuizError] = useState('')
  const [debugError, setDebugError] = useState('')
  const [messages, setMessages] = useState(() => readVideoChatHistory(readCurrentVideo()?.video_id))
  const [summary, setSummary] = useState(null)
  const [notes, setNotes] = useState(null)
  const [quiz, setQuiz] = useState(null)
  const [debugResult, setDebugResult] = useState(null)
  const [activeTab, setActiveTab] = useState(() => readActiveWorkspaceTab())
  const [isLoading, setIsLoading] = useState(false)
  const [isAsking, setIsAsking] = useState(false)
  const [isSummaryLoading, setIsSummaryLoading] = useState(false)
  const [isNotesLoading, setIsNotesLoading] = useState(false)
  const [isQuizLoading, setIsQuizLoading] = useState(false)
  const [isDebugLoading, setIsDebugLoading] = useState(false)
  const [isHistoryLoading, setIsHistoryLoading] = useState(false)
  const [isRebuildingIndex, setIsRebuildingIndex] = useState(false)
  const [ingestStage, setIngestStage] = useState('')

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

  useEffect(() => {
    if (video?.video_id) {
      loadBackendChatHistory(video.video_id)
    }
  }, [video?.video_id])

  async function handleIngest(url) {
    setIsLoading(true)
    const ingestTimers = startIngestStages(setIngestStage)
    setError('')
    setChatError('')
    setSummaryError('')
    setNotesError('')
    setQuizError('')
    setDebugError('')
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
      ingestTimers.forEach((timerId) => clearTimeout(timerId))
      setIngestStage('')
      setIsLoading(false)
    }
  }

  async function handleAsk(question, retrievalMode, sourceChunkIds = []) {
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
        sourceChunkIds,
      })
      setMessages((currentMessages) => {
        const nextMessages = [
          normalizeChatMessage(response, {
            question,
            selectedForExport: true,
          }),
          ...currentMessages,
        ]
        saveVideoChatHistory(video.video_id, nextMessages)
        return nextMessages
      })
    } catch (requestError) {
      setChatError(requestError.message)
    } finally {
      setIsAsking(false)
    }
  }

  function handleRegenerateAnswer(message) {
    handleAsk(
      message.question,
      message.retrievalMode || 'hybrid',
      message.sources?.map((source) => source.chunk_id) || [],
    )
  }

  function handleAskWithSource(message, source) {
    handleAsk(
      message.question,
      message.retrievalMode || 'hybrid',
      [source.chunk_id],
    )
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

  async function handleGenerateNotes({ mode, learningGoal, force }) {
    if (!video) {
      return
    }

    setIsNotesLoading(true)
    setNotesError('')

    try {
      const response = await generateStudyNotes({
        videoId: video.video_id,
        mode,
        learningGoal,
        force,
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

  function handleChangeTab(tabId) {
    setActiveTab(tabId)
    localStorage.setItem(ACTIVE_TAB_KEY, tabId)
  }

  function handleAskDebugQuestion() {
    if (!debugResult) {
      return
    }

    handleChangeTab('chat')
    handleAsk(
      debugResult.question,
      debugResult.retrieval_mode,
      debugResult.chunks.map((chunk) => chunk.chunk_id),
    )
  }

  function handleToggleMessageExport(messageId) {
    if (!video) {
      return
    }

    setMessages((currentMessages) => {
      const nextMessages = currentMessages.map((message) =>
        message.id === messageId
          ? { ...message, selectedForExport: !message.selectedForExport }
          : message,
      )
      saveVideoChatHistory(video.video_id, nextMessages)
      return nextMessages
    })
  }

  async function handleClearChatHistory() {
    if (!video) {
      return
    }

    try {
      await clearBackendChatHistory(video.video_id)
    } catch {
      // Local chat history still clears when backend history is unavailable.
    } finally {
      saveVideoChatHistory(video.video_id, [])
      setMessages([])
    }
  }

  async function handleRebuildIndex(videoId) {
    setIsRebuildingIndex(true)
    setError('')

    try {
      await rebuildVideoIndex(videoId)
    } catch (requestError) {
      setError(requestError.message)
    } finally {
      setIsRebuildingIndex(false)
    }
  }

  async function loadBackendChatHistory(videoId) {
    try {
      const response = await getChatHistory(videoId)
      const syncedMessages = response.messages.map((message) => normalizeChatMessage(message))
      setMessages(syncedMessages)
      saveVideoChatHistory(videoId, syncedMessages)
    } catch {
      setMessages(readVideoChatHistory(videoId))
    }
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
    setMessages(readVideoChatHistory(normalizedVideo.video_id))
    loadBackendChatHistory(normalizedVideo.video_id)
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
        <VideoIngestForm
          onSubmit={handleIngest}
          isLoading={isLoading}
          ingestStage={ingestStage}
        />

        {error ? <p className="error-message">{error}</p> : null}

        <VideoHistory
          videos={videoHistory}
          currentVideoId={video?.video_id}
          onSelect={handleSelectVideo}
          onDelete={handleDeleteVideo}
          isLoading={isHistoryLoading}
        />

        <VideoResult
          video={video}
          onRebuildIndex={handleRebuildIndex}
          isRebuilding={isRebuildingIndex}
        />

        <section className="workspace-tabs" aria-label="Learning workspace">
          <div className="tab-list" role="tablist" aria-label="Workspace sections">
            {WORKSPACE_TABS.map((tab) => (
              <button
                type="button"
                role="tab"
                aria-selected={activeTab === tab.id}
                className="tab-button"
                key={tab.id}
                onClick={() => handleChangeTab(tab.id)}
              >
                {tab.label}
              </button>
            ))}
          </div>

          <div className="tab-panel" role="tabpanel">
            {activeTab === 'chat' ? (
              <ChatPanel
                video={video}
                messages={messages}
                onAsk={handleAsk}
                onRegenerate={handleRegenerateAnswer}
                onAskWithSource={handleAskWithSource}
                onToggleExport={handleToggleMessageExport}
                onClearHistory={handleClearChatHistory}
                isAsking={isAsking}
                error={chatError}
              />
            ) : null}

            {activeTab === 'summary' ? (
              <SummaryPanel
                video={video}
                summary={summary}
                onGenerate={handleGenerateSummary}
                isLoading={isSummaryLoading}
                error={summaryError}
              />
            ) : null}

            {activeTab === 'notes' ? (
              <NotesPanel
                video={video}
                notes={notes}
                onGenerate={handleGenerateNotes}
                isLoading={isNotesLoading}
                error={notesError}
              />
            ) : null}

            {activeTab === 'quiz' ? (
              <QuizPanel
                video={video}
                quiz={quiz}
                onGenerate={handleGenerateQuiz}
                isLoading={isQuizLoading}
                error={quizError}
              />
            ) : null}

            {activeTab === 'export' ? (
              <ExportPanel
                video={video}
                summary={summary}
                notes={notes}
                quiz={quiz}
                selectedMessages={messages.filter((message) => message.selectedForExport)}
              />
            ) : null}

            {activeTab === 'debug' ? (
              <RagDebugPanel
                video={video}
                debugResult={debugResult}
                onRetrieve={handleDebugRetrieve}
                onAskInChat={handleAskDebugQuestion}
                isLoading={isDebugLoading}
                error={debugError}
              />
            ) : null}
          </div>
        </section>
      </section>
    </main>
  )
}

function readActiveWorkspaceTab() {
  const storedTab = localStorage.getItem(ACTIVE_TAB_KEY)
  return WORKSPACE_TABS.some((tab) => tab.id === storedTab) ? storedTab : 'chat'
}

function startIngestStages(setIngestStage) {
  setIngestStage('Fetching transcript...')
  return [
    setTimeout(() => setIngestStage('Chunking transcript...'), 700),
    setTimeout(() => setIngestStage('Indexing BM25 and vector store...'), 1400),
  ]
}

function normalizeVideo(video) {
  return {
    ...video,
    status: video.status || 'cached',
    updated_at: video.updated_at || new Date().toISOString(),
  }
}

function normalizeChatMessage(message, overrides = {}) {
  return {
    id: message.message_id || overrides.id || `${Date.now()}`,
    messageId: message.message_id || overrides.messageId || null,
    question: overrides.question || message.question,
    answer: message.answer,
    retrievalMode: message.retrieval_mode || message.retrievalMode || 'hybrid',
    generation: message.generation,
    sources: message.sources || [],
    groundednessWarning: message.groundedness_warning || message.groundednessWarning || null,
    selectedForExport: overrides.selectedForExport ?? true,
    createdAt: message.created_at || new Date().toISOString(),
  }
}

export default App
