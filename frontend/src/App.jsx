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
import {
  cancelIngestJob,
  createIngestJob,
  deleteVideo,
  getIngestJob,
  getVideo,
  listVideos,
  rebuildVideoIndex,
  retryIngestJob,
} from './features/video/videoApi'
import { VideoHistory } from './features/video/VideoHistory'
import { VideoIngestForm } from './features/video/VideoIngestForm'
import { VideoResult } from './features/video/VideoResult'
import { ACTIVE_INGEST_STATUSES } from './features/video/ingestJobState'
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
  { id: 'chat', label: 'Chat', description: 'Ask grounded questions' },
  { id: 'summary', label: 'Summary', description: 'Short, detailed, timeline' },
  { id: 'notes', label: 'Notes', description: 'Study notes and cards' },
  { id: 'quiz', label: 'Quiz', description: 'Practice and review' },
  { id: 'export', label: 'Export', description: 'Markdown handoff' },
  { id: 'debug', label: 'Debug', description: 'Inspect retrieval' },
]
const ACTIVE_TAB_KEY = 'youtube-qa-active-workspace-tab'
const ACTIVE_INGEST_JOB_KEY = 'youtube-qa-active-ingest-job'

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
  const [ingestJob, setIngestJob] = useState(null)
  const [isAsking, setIsAsking] = useState(false)
  const [isSummaryLoading, setIsSummaryLoading] = useState(false)
  const [isNotesLoading, setIsNotesLoading] = useState(false)
  const [isQuizLoading, setIsQuizLoading] = useState(false)
  const [isDebugLoading, setIsDebugLoading] = useState(false)
  const [isHistoryLoading, setIsHistoryLoading] = useState(false)
  const [isRebuildingIndex, setIsRebuildingIndex] = useState(false)

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
    const jobId = localStorage.getItem(ACTIVE_INGEST_JOB_KEY)
    if (!jobId) {
      return
    }
    let active = true
    resumeIngestJob(jobId, () => active)
    return () => {
      active = false
    }
    // The persisted identifier is the only input; handlers intentionally stay local to this component.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => {
    if (video?.video_id) {
      loadBackendChatHistory(video.video_id)
    }
  }, [video?.video_id])

  async function handleIngest(url) {
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
      const job = await createIngestJob(url)
      setIngestJob(job)
      localStorage.setItem(ACTIVE_INGEST_JOB_KEY, job.job_id)
      await resumeIngestJob(job.job_id)
    } catch (requestError) {
      setError(requestError.message)
    }
  }

  async function resumeIngestJob(jobId, isActive = () => true) {
    let job = await getIngestJob(jobId)
    while (isActive()) {
      setIngestJob(job)
      if (!ACTIVE_INGEST_STATUSES.has(job.status)) {
        if (job.status === 'ready') {
          applySelectedVideo(await getVideo(job.video_id))
        }
        return
      }
      await wait(750)
      job = await getIngestJob(jobId)
    }
  }

  async function handleRetryIngest() {
    if (!ingestJob) return
    setError('')
    try {
      const retried = await retryIngestJob(ingestJob.job_id)
      setIngestJob(retried)
      await resumeIngestJob(retried.job_id)
    } catch (requestError) {
      setError(requestError.message)
    }
  }

  async function handleCancelIngest() {
    if (!ingestJob) return
    setError('')
    try {
      setIngestJob(await cancelIngestJob(ingestJob.job_id))
    } catch (requestError) {
      setError(requestError.message)
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

  async function handleGenerateSummary({ mode, force = false }) {
    if (!video) {
      return
    }

    setIsSummaryLoading(true)
    setSummaryError('')

    try {
      const response = await generateVideoSummary({
        videoId: video.video_id,
        mode,
        force,
      })
      setSummary(response)
    } catch (requestError) {
      setSummaryError(requestError.message)
    } finally {
      setIsSummaryLoading(false)
    }
  }

  async function handleGenerateNotes({ mode, length, learningGoal, force }) {
    if (!video) {
      return
    }

    setIsNotesLoading(true)
    setNotesError('')

    try {
      const response = await generateStudyNotes({
        videoId: video.video_id,
        mode,
        length,
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

  async function handleGenerateQuiz({
    questionCount,
    difficulty,
    questionType,
    mode,
    force,
    sourceChunkIds,
  }) {
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
        mode,
        force,
        sourceChunkIds,
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
        <h1>Turn YouTube transcripts into a focused learning workspace.</h1>
        <p className="intro-copy">
          Ingest a video once, then ask questions, generate summaries, build study notes,
          create quizzes and export a clean study pack with timestamped sources.
        </p>
      </section>

      <section className="workspace" aria-label="Video learning workspace">
        <aside className="workspace-sidebar" aria-label="Video controls">
          <VideoIngestForm
            onSubmit={handleIngest}
            onRetry={handleRetryIngest}
            onCancel={handleCancelIngest}
            ingestJob={ingestJob}
          />

          {error ? <p className="error-message">{error}</p> : null}

          <VideoHistory
            videos={videoHistory}
            currentVideoId={video?.video_id}
            onSelect={handleSelectVideo}
            onDelete={handleDeleteVideo}
            isLoading={isHistoryLoading}
          />
        </aside>

        <section className="workspace-main" aria-label="Learning tools">
          <VideoResult
            video={video}
            onRebuildIndex={handleRebuildIndex}
            isRebuilding={isRebuildingIndex}
          />

          <div className="workspace-status" aria-label="Workspace status">
            <StatusMetric label="Chat" value={`${messages.length} saved`} />
            <StatusMetric label="Summary" value={summary ? statusValue(summary) : 'Not generated'} />
            <StatusMetric label="Notes" value={notes ? statusValue(notes) : 'Not generated'} />
            <StatusMetric label="Quiz" value={quiz ? `${quiz.questions.length} questions` : 'Not generated'} />
          </div>

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
                  <span>{tab.label}</span>
                  <small>{tab.description}</small>
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
      </section>
    </main>
  )
}

function readActiveWorkspaceTab() {
  const storedTab = localStorage.getItem(ACTIVE_TAB_KEY)
  return WORKSPACE_TABS.some((tab) => tab.id === storedTab) ? storedTab : 'chat'
}

function wait(milliseconds) {
  return new Promise((resolve) => setTimeout(resolve, milliseconds))
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

function StatusMetric({ label, value }) {
  return (
    <div className="status-metric">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  )
}

function statusValue(output) {
  if (output.cached) {
    return 'Cached'
  }

  return output.generation?.generation_mode || 'New'
}

export default App
