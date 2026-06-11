import { API_BASE_URL } from '../../shared/config/api'

export async function retrieveDebugContext({
  videoId,
  question,
  retrievalMode,
  topK,
}) {
  const response = await fetch(`${API_BASE_URL}/debug/retrieve`, {
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
  })

  const data = await response.json()

  if (!response.ok) {
    throw new Error(data.detail || 'Could not run RAG debug.')
  }

  return data
}
