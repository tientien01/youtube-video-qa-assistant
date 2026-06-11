import { API_BASE_URL } from '../../shared/config/api'
import { requestJson } from '../../shared/api/request'

export async function generateStudyNotes({
  videoId,
  mode = 'concise',
  length = 'medium',
  learningGoal = '',
  force = false,
}) {
  return requestJson(`${API_BASE_URL}/videos/${videoId}/study-notes`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      mode,
      length,
      learning_goal: learningGoal || null,
      force,
    }),
  }, 'Could not generate study notes.')
}
