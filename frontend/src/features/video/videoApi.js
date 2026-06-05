const API_BASE_URL = 'http://127.0.0.1:8000/api/v1'

export async function ingestVideo(url) {
  const response = await fetch(`${API_BASE_URL}/videos/ingest`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ url }),
  })

  const data = await response.json()

  if (!response.ok) {
    throw new Error(data.detail || 'Không thể ingest video.')
  }

  return data
}

export async function listVideos() {
  const response = await fetch(`${API_BASE_URL}/videos`)
  const data = await response.json()

  if (!response.ok) {
    throw new Error(data.detail || 'Không thể tải danh sách video.')
  }

  return data
}

export async function getVideo(videoId) {
  const response = await fetch(`${API_BASE_URL}/videos/${videoId}`)
  const data = await response.json()

  if (!response.ok) {
    throw new Error(data.detail || 'Không thể tải thông tin video.')
  }

  return data
}

export async function deleteVideo(videoId) {
  const response = await fetch(`${API_BASE_URL}/videos/${videoId}`, {
    method: 'DELETE',
  })
  const data = await response.json()

  if (!response.ok) {
    throw new Error(data.detail || 'Không thể xóa video.')
  }

  return data
}
