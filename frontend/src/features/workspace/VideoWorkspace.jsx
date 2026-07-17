import { useCallback, useMemo, useState } from 'react'
import { WorkspaceChat } from '../chat/WorkspaceChat'
import { EvidencePanel } from '../evidence/EvidencePanel'
import { YouTubePlayer } from '../player/YouTubePlayer'
import { TranscriptPanel } from '../transcript/TranscriptPanel'

export function VideoWorkspace({ video, transcript, transcriptLoading, transcriptError, messages, isAsking, chatError, onAsk, onClear }) {
  const [currentTime, setCurrentTime] = useState(0)
  const [seekRequest, setSeekRequest] = useState(null)
  const [selectedSource, setSelectedSource] = useState(null)
  const latestSources = useMemo(() => messages[0]?.sources || [], [messages])
  const seek = useCallback((seconds, source) => {
    setSelectedSource(source)
    setSeekRequest({ seconds, token: Date.now() })
  }, [])
  const selectEvidence = useCallback((source, action = 'play') => {
    setSelectedSource(source)
    if (action === 'play') setSeekRequest({ seconds: source.start_seconds, token: Date.now() })
    if (action === 'transcript') document.querySelector('.transcript-panel')?.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
  }, [])

  return (
    <div className="video-workspace">
      <section className="video-column">
        <div className="player-panel"><YouTubePlayer video={video} seekRequest={seekRequest} onTime={setCurrentTime} /><div className="player-caption"><div><p className="panel-kicker">Now learning</p><h1>{video.title}</h1></div><span>{video.channel_title || 'Unknown channel'}</span></div></div>
        <TranscriptPanel transcript={transcript} loading={transcriptLoading} error={transcriptError} currentTime={currentTime} selectedSource={selectedSource} onSeek={seek} />
      </section>
      <section className="assistant-column">
        <WorkspaceChat messages={messages} isAsking={isAsking} error={chatError} onAsk={onAsk} onSelectSource={selectEvidence} onClear={onClear} />
        <EvidencePanel sources={latestSources} selectedSource={selectedSource} onSelect={selectEvidence} />
      </section>
    </div>
  )
}
