import { API_BASE_URL } from '../../shared/config/api'
import { requestJson } from '../../shared/api/request'

export async function ingestVideo(url) {
  return requestJson(`${API_BASE_URL}/videos/ingest`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ url }),
  }, 'Could not ingest this video.')
}

export async function listVideos() {
  return requestJson(`${API_BASE_URL}/videos`, {}, 'Could not load the video library.')
}

export async function getVideo(videoId) {
  return requestJson(`${API_BASE_URL}/videos/${videoId}`, {}, 'Could not load this video.')
}

export async function deleteVideo(videoId) {
  return requestJson(`${API_BASE_URL}/videos/${videoId}`, {
    method: 'DELETE',
  }, 'Could not delete this video.')
}

export async function rebuildVideoIndex(videoId) {
  return requestJson(`${API_BASE_URL}/videos/${videoId}/rebuild-index`, {
    method: 'POST',
  }, 'Could not rebuild the index.')
}
