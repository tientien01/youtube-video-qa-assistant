import { API_BASE_URL } from '../../shared/config/api'
import { requestJson } from '../../shared/api/request'

export async function askVideoQuestion({
  videoId,
  question,
  retrievalMode,
  sourceChunkIds = [],
}) {
  return requestJson(`${API_BASE_URL}/chat/ask`, {
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
  }, 'Could not send this question.')
}

export async function getChatHistory(videoId) {
  return requestJson(`${API_BASE_URL}/chat/history/${videoId}`, {}, 'Could not load chat history.')
}

export async function clearBackendChatHistory(videoId) {
  return requestJson(`${API_BASE_URL}/chat/history/${videoId}`, {
    method: 'DELETE',
  }, 'Could not clear chat history.')
}
