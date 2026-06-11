import { API_BASE_URL } from '../../shared/config/api'

export async function generateVideoQuiz({
  videoId,
  questionCount,
  difficulty,
  questionType,
  mode = 'practice',
  force = false,
  sourceChunkIds = [],
}) {
  const response = await fetch(`${API_BASE_URL}/videos/${videoId}/quiz`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      question_count: questionCount,
      difficulty,
      question_type: questionType,
      mode,
      force,
      source_chunk_ids: sourceChunkIds,
    }),
  })

  const data = await response.json()

  if (!response.ok) {
    throw new Error(data.detail || 'Could not generate a quiz.')
  }

  return data
}
