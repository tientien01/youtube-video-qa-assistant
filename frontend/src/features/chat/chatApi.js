const API_BASE_URL = 'http://127.0.0.1:8000/api/v1'

export async function askVideoQuestion({ videoId, question, retrievalMode }) {
  const response = await fetch(`${API_BASE_URL}/chat/ask`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      video_id: videoId,
      question,
      retrieval_mode: retrievalMode,
    }),
  })

  const data = await response.json()

  if (!response.ok) {
    throw new Error(data.detail || 'Không thể gửi câu hỏi.')
  }

  return data
}
