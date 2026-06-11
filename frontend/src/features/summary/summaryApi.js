import { API_BASE_URL } from '../../shared/config/api'
import { requestJson } from '../../shared/api/request'

export async function generateVideoSummary({ videoId, mode, force = false }) {
  return requestJson(`${API_BASE_URL}/videos/${videoId}/summary`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ mode, force }),
  }, 'Could not generate a summary.')
}
