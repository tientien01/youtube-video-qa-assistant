import { useEffect, useId, useRef } from 'react'

export function YouTubePlayer({ video, seekRequest, onTime }) {
  const id = `youtube-player-${useId().replaceAll(':', '')}`
  const playerRef = useRef(null)

  useEffect(() => {
    let cancelled = false
    loadYouTubeApi().then(() => {
      if (cancelled || !window.YT?.Player) return
      playerRef.current = new window.YT.Player(id, {
        videoId: video.video_id,
        playerVars: { enablejsapi: 1, rel: 0 },
      })
    })
    const timer = window.setInterval(() => {
      const seconds = playerRef.current?.getCurrentTime?.()
      if (typeof seconds === 'number') onTime(seconds)
    }, 500)
    return () => {
      cancelled = true
      window.clearInterval(timer)
      playerRef.current?.destroy?.()
    }
  }, [id, onTime, video.video_id])

  useEffect(() => {
    if (!seekRequest) return
    playerRef.current?.seekTo?.(seekRequest.seconds, true)
    playerRef.current?.playVideo?.()
  }, [seekRequest])

  return <div className="video-player" id={id} aria-label={`YouTube player for ${video.title}`} />
}

let apiPromise
function loadYouTubeApi() {
  if (window.YT?.Player) return Promise.resolve()
  if (apiPromise) return apiPromise
  apiPromise = new Promise((resolve) => {
    const previous = window.onYouTubeIframeAPIReady
    window.onYouTubeIframeAPIReady = () => { previous?.(); resolve() }
    const script = document.createElement('script')
    script.src = 'https://www.youtube.com/iframe_api'
    script.async = true
    document.head.appendChild(script)
  })
  return apiPromise
}
