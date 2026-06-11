import { API_BASE_URL } from '../../shared/config/api'
import { requestJson } from '../../shared/api/request'

export async function retrieveDebugContext({
  videoId,
  question,
  retrievalMode,
  topK,
}) {
  return requestJson(`${API_BASE_URL}/debug/retrieve`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      video_id: videoId,
      question,
      retrieval_mode: retrievalMode,
      top_k: topK,
    }),
  }, 'Could not run RAG debug.')
}
