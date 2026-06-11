const API_BASE_URL = 'http://127.0.0.1:8000/api/v1'

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
    throw new Error(data.detail || 'Không thể tạo study notes.')
  }

  return data
}
