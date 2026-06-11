export const API_BASE_URL = normalizeApiBaseUrl(
  import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000/api/v1',
)

function normalizeApiBaseUrl(value) {
  return value.replace(/\/+$/, '')
}
