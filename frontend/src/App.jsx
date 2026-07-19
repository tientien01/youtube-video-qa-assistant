import { useEffect, useState } from 'react'
import './App.css'
import { ApplicationShell } from './app/ApplicationShell'
import { parseRoute, useRoute } from './app/router'
import { askVideoQuestion, clearBackendChatHistory, getChatHistory } from './features/chat/chatApi'
import { retrieveDebugContext } from './features/debug/debugApi'
import { RagDebugPanel } from './features/debug/RagDebugPanel'
import { ExportPanel } from './features/export/ExportPanel'
import { generateStudyNotes } from './features/notes/notesApi'
import { NotesPanel } from './features/notes/NotesPanel'
import { generateVideoQuiz } from './features/quiz/quizApi'
import { QuizPanel } from './features/quiz/QuizPanel'
import { getRuntimeHealth } from './features/runtime-health/runtimeApi'
import { generateVideoSummary } from './features/summary/summaryApi'
import { SummaryPanel } from './features/summary/SummaryPanel'
import {
  cancelIngestJob,
  createIngestJob,
  deleteVideo,
  getIngestJob,
  getVideo,
  getVideoTranscript,
  listVideos,
  retryIngestJob,
} from './features/video/videoApi'
import { VideoHistory } from './features/video/VideoHistory'
import { VideoIngestForm } from './features/video/VideoIngestForm'
import { ACTIVE_INGEST_STATUSES } from './features/video/ingestJobState'
import {
  readCurrentVideo,
  readVideoChatHistory,
  readVideoHistory,
  removeVideoFromStorage,
  replaceVideoHistory,
  saveCurrentVideo,
  saveVideoChatHistory,
  saveVideoToHistory,
} from './features/video/videoStorage'
import { VideoWorkspace } from './features/workspace/VideoWorkspace'

const ACTIVE_INGEST_JOB_KEY = 'youtube-qa-active-ingest-job'
const LANGUAGE_KEY = 'youtube-qa-language'

function App() {
  const router = useRoute()
  const route = parseRoute(router.path)
  const [video, setVideo] = useState(() => readCurrentVideo())
  const [videoHistory, setVideoHistory] = useState(() => readVideoHistory())
  const [ingestJob, setIngestJob] = useState(null)
  const [messages, setMessages] = useState(() => readVideoChatHistory(readCurrentVideo()?.video_id))
  const [transcript, setTranscript] = useState(null)
  const [health, setHealth] = useState(null)
  const [summary, setSummary] = useState(null)
  const [notes, setNotes] = useState(null)
  const [quiz, setQuiz] = useState(null)
  const [debugResult, setDebugResult] = useState(null)
  const [language, setLanguage] = useState(() => localStorage.getItem(LANGUAGE_KEY) || 'vi')
  const [error, setError] = useState('')
  const [chatError, setChatError] = useState('')
  const [transcriptError, setTranscriptError] = useState('')
  const [healthError, setHealthError] = useState('')
  const [isHistoryLoading, setIsHistoryLoading] = useState(true)
  const [isTranscriptLoading, setIsTranscriptLoading] = useState(() => Boolean(readCurrentVideo()?.video_id))
  const [isAsking, setIsAsking] = useState(false)
  const [isSummaryLoading, setIsSummaryLoading] = useState(false)
  const [isNotesLoading, setIsNotesLoading] = useState(false)
  const [isQuizLoading, setIsQuizLoading] = useState(false)
  const [isDebugLoading, setIsDebugLoading] = useState(false)

  useEffect(() => {
    let active = true
    listVideos()
      .then((items) => active && setVideoHistory(replaceVideoHistory(items)))
      .catch((requestError) => active && setError(requestError.message))
      .finally(() => active && setIsHistoryLoading(false))
    getRuntimeHealth()
      .then((value) => active && setHealth(value))
      .catch((requestError) => active && setHealthError(requestError.message))
    return () => { active = false }
  }, [])

  useEffect(() => {
    const jobId = localStorage.getItem(ACTIVE_INGEST_JOB_KEY)
    if (!jobId) return
    let active = true
    resumeIngestJob(jobId, () => active)
    return () => { active = false }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => {
    if (route.page !== 'workspace' || !route.videoId || video?.video_id === route.videoId) return
    getVideo(route.videoId).then((nextVideo) => applySelectedVideo(nextVideo, false)).catch((requestError) => setError(requestError.message))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [route.page, route.videoId, video?.video_id])

  useEffect(() => {
    if (!video?.video_id) return
    let active = true
    getVideoTranscript(video.video_id)
      .then((value) => active && setTranscript(value))
      .catch((requestError) => active && setTranscriptError(requestError.message))
      .finally(() => active && setIsTranscriptLoading(false))
    getChatHistory(video.video_id)
      .then((response) => {
        if (!active) return
        const synced = response.messages.map((message) => normalizeChatMessage(message))
        setMessages(synced)
        saveVideoChatHistory(video.video_id, synced)
      })
      .catch(() => active && setMessages(readVideoChatHistory(video.video_id)))
    return () => { active = false }
  }, [video?.video_id])

  function changeLanguage(value) {
    setLanguage(value)
    localStorage.setItem(LANGUAGE_KEY, value)
  }

  async function handleIngest(url) {
    setError('')
    try {
      const job = await createIngestJob(url)
      setIngestJob(job)
      localStorage.setItem(ACTIVE_INGEST_JOB_KEY, job.job_id)
      await resumeIngestJob(job.job_id)
    } catch (requestError) { setError(requestError.message) }
  }

  async function resumeIngestJob(jobId, isActive = () => true) {
    let job = await getIngestJob(jobId)
    while (isActive()) {
      setIngestJob(job)
      if (!ACTIVE_INGEST_STATUSES.has(job.status)) {
        if (job.status === 'ready') applySelectedVideo(await getVideo(job.video_id))
        return
      }
      await wait(750)
      job = await getIngestJob(jobId)
    }
  }

  async function handleRetryIngest() {
    if (!ingestJob) return
    try {
      const job = await retryIngestJob(ingestJob.job_id)
      setIngestJob(job)
      await resumeIngestJob(job.job_id)
    } catch (requestError) { setError(requestError.message) }
  }

  async function handleCancelIngest() {
    if (!ingestJob) return
    try { setIngestJob(await cancelIngestJob(ingestJob.job_id)) } catch (requestError) { setError(requestError.message) }
  }

  async function handleAsk(question, retrievalMode = 'hybrid', sourceChunkIds = []) {
    if (!video) return
    setIsAsking(true)
    setChatError('')
    try {
      const response = await askVideoQuestion({
        videoId: video.video_id,
        question,
        retrievalMode,
        sourceChunkIds,
        answerLanguage: language,
      })
      setMessages((current) => {
        const next = [normalizeChatMessage(response, { question }), ...current]
        saveVideoChatHistory(video.video_id, next)
        return next
      })
    } catch (requestError) { setChatError(requestError.message) } finally { setIsAsking(false) }
  }

  async function handleClearChatHistory() {
    if (!video) return
    try { await clearBackendChatHistory(video.video_id) } catch { /* local state still clears */ }
    setMessages([])
    saveVideoChatHistory(video.video_id, [])
  }

  function applySelectedVideo(nextVideo, navigate = true) {
    const normalized = normalizeVideo(nextVideo)
    setVideo(normalized)
    saveCurrentVideo(normalized)
    setVideoHistory(saveVideoToHistory(normalized))
    setMessages(readVideoChatHistory(normalized.video_id))
    setTranscript(null)
    setTranscriptError('')
    setIsTranscriptLoading(true)
    setSummary(null); setNotes(null); setQuiz(null); setDebugResult(null)
    if (navigate) router.navigate(`/library/${encodeURIComponent(normalized.video_id)}`)
  }

  async function handleDeleteVideo(videoId) {
    try { await deleteVideo(videoId) } catch (requestError) { setError(requestError.message); return }
    setError('')
    setVideoHistory(removeVideoFromStorage(videoId))
    if (video?.video_id === videoId) { setVideo(null); router.navigate('/library') }
  }

  async function handleGenerateSummary(options) {
    if (!video) return
    setIsSummaryLoading(true)
    try { setSummary(await generateVideoSummary({ videoId: video.video_id, ...options })) } finally { setIsSummaryLoading(false) }
  }

  async function handleGenerateNotes(options) {
    if (!video) return
    setIsNotesLoading(true)
    try { setNotes(await generateStudyNotes({ videoId: video.video_id, ...options })) } finally { setIsNotesLoading(false) }
  }

  async function handleGenerateQuiz(options) {
    if (!video) return
    setIsQuizLoading(true)
    try { setQuiz(await generateVideoQuiz({ videoId: video.video_id, ...options })) } finally { setIsQuizLoading(false) }
  }

  async function handleDebugRetrieve(options) {
    if (!video) return
    setIsDebugLoading(true)
    try { setDebugResult(await retrieveDebugContext({ videoId: video.video_id, ...options })) } finally { setIsDebugLoading(false) }
  }

  const page = renderPage({
    route, router, video, videoHistory, ingestJob, error, isHistoryLoading, transcript, transcriptError,
    isTranscriptLoading, messages, isAsking, chatError, summary, notes, quiz, debugResult,
    isSummaryLoading, isNotesLoading, isQuizLoading, isDebugLoading,
    handleIngest, handleRetryIngest, handleCancelIngest, applySelectedVideo, handleDeleteVideo,
    handleAsk, handleClearChatHistory, handleGenerateSummary, handleGenerateNotes, handleGenerateQuiz, handleDebugRetrieve,
  })

  return <ApplicationShell route={route} navigate={router.navigate} video={video} health={health} healthError={healthError} language={language} onLanguage={changeLanguage}>{page}</ApplicationShell>
}

function renderPage(context) {
  const { route, router, video } = context
  if (route.page === 'workspace' && video) return <VideoWorkspace video={video} transcript={context.transcript} transcriptLoading={context.isTranscriptLoading} transcriptError={context.transcriptError} messages={context.messages} isAsking={context.isAsking} chatError={context.chatError} onAsk={context.handleAsk} onClear={context.handleClearChatHistory} />
  if (route.page === 'home' || route.page === 'library') return <LibraryPage home={route.page === 'home'} {...context} />
  if (route.page === 'learning') return <SummaryPage {...context} />
  if (route.page === 'notes') return <NotesPage {...context} />
  if (route.page === 'quizzes') return <QuizzesPage {...context} />
  if (route.page === 'export') return <ExportPage {...context} />
  if (route.page === 'developer') return <RagDebugPanel video={video} debugResult={context.debugResult} onRetrieve={context.handleDebugRetrieve} onAskInChat={() => router.navigate(video ? `/library/${video.video_id}` : '/library')} isLoading={context.isDebugLoading} error="" />
  if (route.page === 'settings') return <SimplePage title="Settings" text="Runtime settings are read from the backend environment. Edit the local .env and restart the API to apply provider or model changes." />
  return <SimplePage title="Page unavailable" text="This destination is not part of the working Local V1 routes." />
}

function LibraryPage({ home, video, videoHistory, ingestJob, error, isHistoryLoading, handleIngest, handleRetryIngest, handleCancelIngest, applySelectedVideo, handleDeleteVideo }) {
  return <div className="library-page"><header className="page-heading"><p className="panel-kicker">{home ? 'Local-first learning' : 'Your collection'}</p><h1>{home ? 'Learn from any supported YouTube video.' : 'Video library'}</h1><p>Ingest once, then study with transcript-grounded answers and timestamped evidence.</p></header><div className="library-grid"><VideoIngestForm onSubmit={handleIngest} onRetry={handleRetryIngest} onCancel={handleCancelIngest} ingestJob={ingestJob} />{error ? <p className="error-message">{error}</p> : null}<VideoHistory videos={videoHistory} currentVideoId={video?.video_id} onSelect={applySelectedVideo} onDelete={handleDeleteVideo} isLoading={isHistoryLoading} /></div></div>
}

function SummaryPage(context) {
  return <ArtifactPage kicker="Study tool" title="Summary" description="Generate a timestamped overview from the selected video."><SummaryPanel video={context.video} summary={context.summary} onGenerate={context.handleGenerateSummary} isLoading={context.isSummaryLoading} error="" /></ArtifactPage>
}

function NotesPage(context) {
  return <ArtifactPage kicker="Study tool" title="Study Notes" description="Turn the selected video into structured notes for your learning goal."><NotesPanel video={context.video} notes={context.notes} onGenerate={context.handleGenerateNotes} isLoading={context.isNotesLoading} error="" /></ArtifactPage>
}

function QuizzesPage(context) {
  return <ArtifactPage kicker="Practice" title="Quizzes" description="Generate grounded questions and review every answer with timestamped evidence."><QuizPanel video={context.video} quiz={context.quiz} onGenerate={context.handleGenerateQuiz} isLoading={context.isQuizLoading} error="" /></ArtifactPage>
}

function ExportPage(context) {
  return <ArtifactPage kicker="Portable learning" title="Export" description="Build a Markdown study pack from the artifacts you have generated."><ExportPanel video={context.video} summary={context.summary} notes={context.notes} quiz={context.quiz} selectedMessages={context.messages} /></ArtifactPage>
}

function ArtifactPage({ kicker, title, description, children }) {
  return <div className="learning-page"><header className="page-heading"><p className="panel-kicker">{kicker}</p><h1>{title}</h1><p>{description}</p></header><div className="learning-tools">{children}</div></div>
}

function SimplePage({ title, text }) { return <section className="simple-page"><h1>{title}</h1><p>{text}</p></section> }

function normalizeVideo(video) { return { ...video, status: video.status || 'cached', updated_at: video.updated_at || new Date().toISOString() } }
function normalizeChatMessage(message, overrides = {}) { return { id: message.message_id || `${Date.now()}`, question: overrides.question || message.question, answer: message.answer, answerLanguage: message.answer_language, retrievalMode: message.retrieval_mode || 'hybrid', generation: message.generation, sources: message.sources || [], createdAt: message.created_at || new Date().toISOString() } }
function wait(milliseconds) { return new Promise((resolve) => setTimeout(resolve, milliseconds)) }

export default App
