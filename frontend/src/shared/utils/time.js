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

export function formatDuration(seconds) {
  if (seconds === null || seconds === undefined) {
    return 'Unknown'
  }

  const totalSeconds = Math.max(Math.floor(Number(seconds) || 0), 0)
  const hours = Math.floor(totalSeconds / 3600)
  const minutes = Math.floor((totalSeconds % 3600) / 60)
  const remainingSeconds = totalSeconds % 60

  if (hours > 0) {
    return `${hours}h ${String(minutes).padStart(2, '0')}m ${String(remainingSeconds).padStart(2, '0')}s`
  }

  return `${minutes}m ${String(remainingSeconds).padStart(2, '0')}s`
}
