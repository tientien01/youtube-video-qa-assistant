import { API_BASE_URL } from '../../shared/config/api'

export async function askVideoQuestion({
  videoId,
  question,
  retrievalMode,
  sourceChunkIds = [],
}) {
  const response = await fetch(`${API_BASE_URL}/chat/ask`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      video_id: videoId,
      question,
      retrieval_mode: retrievalMode,
      source_chunk_ids: sourceChunkIds,
    }),
  })

  const data = await response.json()

  if (!response.ok) {
    throw new Error(data.detail || 'Could not send this question.')
  }

  return data
}

export async function getChatHistory(videoId) {
  const response = await fetch(`${API_BASE_URL}/chat/history/${videoId}`)
  const data = await response.json()

  if (!response.ok) {
    throw new Error(data.detail || 'Could not load chat history.')
  }

  return data
}

export async function clearBackendChatHistory(videoId) {
  const response = await fetch(`${API_BASE_URL}/chat/history/${videoId}`, {
    method: 'DELETE',
  })
  const data = await response.json()

  if (!response.ok) {
    throw new Error(data.detail || 'Could not clear chat history.')
  }

  return data
}
