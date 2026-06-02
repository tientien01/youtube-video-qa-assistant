export function formatTimestamp(seconds) {
  const totalSeconds = Math.max(Math.floor(Number(seconds) || 0), 0)
  const minutes = Math.floor(totalSeconds / 60)
  const remainingSeconds = totalSeconds % 60

  return `${String(minutes).padStart(2, '0')}:${String(remainingSeconds).padStart(2, '0')}`
}

export function buildYouTubeTimestampUrl(videoId, seconds) {
  const totalSeconds = Math.max(Math.floor(Number(seconds) || 0), 0)
  return `https://www.youtube.com/watch?v=${videoId}&t=${totalSeconds}s`
}
