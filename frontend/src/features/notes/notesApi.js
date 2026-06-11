import { API_BASE_URL } from '../../shared/config/api'

export async function generateStudyNotes({
  videoId,
  mode = 'concise',
  length = 'medium',
  learningGoal = '',
  force = false,
}) {
  const response = await fetch(`${API_BASE_URL}/videos/${videoId}/study-notes`, {
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
  })

  const data = await response.json()

  if (!response.ok) {
    throw new Error(data.detail || 'Could not generate study notes.')
  }

  return data
}
