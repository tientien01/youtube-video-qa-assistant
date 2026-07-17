export async function requestJson(url, options = {}, fallbackMessage = 'Request failed.') {
  let response
  try {
    response = await fetch(url, options)
  } catch {
    throw new Error(`${fallbackMessage} Check that the backend is running.`)
  }

  const data = await readResponseBody(response)

  if (!response.ok) {
    throw new Error(data?.error?.message || formatErrorDetail(data?.detail) || fallbackMessage)
  }

  return data
}

async function readResponseBody(response) {
  const contentType = response.headers.get('content-type') || ''

  if (contentType.includes('application/json')) {
    try {
      return await response.json()
    } catch {
      return null
    }
  }

  const text = await response.text().catch(() => '')
  return text ? { detail: text } : null
}

function formatErrorDetail(detail) {
  if (typeof detail === 'string') {
    return detail
  }

  if (Array.isArray(detail)) {
    return detail
      .map((item) => item?.msg || item?.message || '')
      .filter(Boolean)
      .join(' ')
  }

  return ''
}
