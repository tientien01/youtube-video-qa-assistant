import { API_BASE_URL } from '../../shared/config/api'
import { requestJson } from '../../shared/api/request'

export async function generateVideoQuiz({
  videoId,
  questionCount,
  difficulty,
  questionType,
  mode = 'practice',
  force = false,
  sourceChunkIds = [],
}) {
  return requestJson(`${API_BASE_URL}/videos/${videoId}/quiz`, {
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
  }, 'Could not generate a quiz.')
}
