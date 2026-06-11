import { API_BASE_URL } from '../../shared/config/api'

export async function generateVideoSummary({ videoId, mode, force = false }) {
  const response = await fetch(`${API_BASE_URL}/videos/${videoId}/summary`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ mode, force }),
  })

  const data = await response.json()

  if (!response.ok) {
    throw new Error(data.detail || 'Could not generate a summary.')
  }

  return data
}
