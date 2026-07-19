const CURRENT_VIDEO_KEY = 'youtube-qa-current-video'
const VIDEO_HISTORY_KEY = 'youtube-qa-video-history'
const CHAT_HISTORY_KEY = 'youtube-qa-chat-history'

export function readCurrentVideo() {
  return readJson(CURRENT_VIDEO_KEY, null)
}

export function saveCurrentVideo(video) {
  if (!video) {
    localStorage.removeItem(CURRENT_VIDEO_KEY)
    return
  }

  localStorage.setItem(CURRENT_VIDEO_KEY, JSON.stringify(video))
}

export function readVideoHistory() {
  const history = readJson(VIDEO_HISTORY_KEY, [])
  return Array.isArray(history) ? history : []
}

export function saveVideoToHistory(video) {
  const nextHistory = mergeVideoHistory([video], readVideoHistory())
  localStorage.setItem(VIDEO_HISTORY_KEY, JSON.stringify(nextHistory))
  return nextHistory
}

export function replaceVideoHistory(videos) {
  return mergeVideoHistory(videos, [])
}

export function mergeVideoHistory(incomingVideos, existingVideos = readVideoHistory()) {
  const videoMap = new Map()

  for (const video of [...incomingVideos, ...existingVideos]) {
    if (!video?.video_id) {
      continue
    }

    const previous = videoMap.get(video.video_id)
    videoMap.set(video.video_id, {
      ...previous,
      ...video,
      updated_at: video.updated_at || previous?.updated_at || new Date().toISOString(),
    })
  }

  const mergedHistory = Array.from(videoMap.values()).sort((left, right) =>
    String(right.updated_at || '').localeCompare(String(left.updated_at || '')),
  )

  localStorage.setItem(VIDEO_HISTORY_KEY, JSON.stringify(mergedHistory))
  return mergedHistory
}

export function removeVideoFromStorage(videoId) {
  const nextHistory = readVideoHistory().filter((video) => video.video_id !== videoId)
  localStorage.setItem(VIDEO_HISTORY_KEY, JSON.stringify(nextHistory))

  const currentVideo = readCurrentVideo()
  if (currentVideo?.video_id === videoId) {
    localStorage.removeItem(CURRENT_VIDEO_KEY)
  }

  deleteVideoChatHistory(videoId)
  return nextHistory
}

export function readVideoChatHistory(videoId) {
  if (!videoId) {
    return []
  }

  const allMessages = readJson(CHAT_HISTORY_KEY, {})
  const messages = allMessages?.[videoId]
  return Array.isArray(messages) ? messages : []
}

export function saveVideoChatHistory(videoId, messages) {
  if (!videoId) {
    return []
  }

  const allMessages = readJson(CHAT_HISTORY_KEY, {})
  const nextMessages = Array.isArray(messages) ? messages : []
  localStorage.setItem(
    CHAT_HISTORY_KEY,
    JSON.stringify({
      ...allMessages,
      [videoId]: nextMessages,
    }),
  )
  return nextMessages
}

export function deleteVideoChatHistory(videoId) {
  const allMessages = readJson(CHAT_HISTORY_KEY, {})
  if (!allMessages || !Object.prototype.hasOwnProperty.call(allMessages, videoId)) {
    return
  }

  const nextMessages = { ...allMessages }
  delete nextMessages[videoId]
  localStorage.setItem(CHAT_HISTORY_KEY, JSON.stringify(nextMessages))
}

function readJson(key, fallbackValue) {
  try {
    const rawValue = localStorage.getItem(key)
    return rawValue ? JSON.parse(rawValue) : fallbackValue
  } catch {
    return fallbackValue
  }
}
