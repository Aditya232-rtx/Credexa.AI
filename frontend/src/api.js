const backendBaseUrl = window.credexa?.backendBaseUrl || 'http://127.0.0.1:8765'

async function requestJson(path, options = {}) {
  const response = await fetch(`${backendBaseUrl}${path}`, {
    headers: {
      ...(options.body instanceof FormData ? {} : { 'Content-Type': 'application/json' }),
      ...(options.headers || {}),
    },
    ...options,
  })

  if (!response.ok) {
    const message = await response.text()
    throw new Error(message || `Request failed with ${response.status}`)
  }

  return response.json()
}

export async function fetchHealth() {
  return requestJson('/health')
}

export async function fetchCases() {
  return requestJson('/cases')
}

export async function fetchCase(caseId) {
  return requestJson(`/cases/${caseId}`)
}

export async function analyzeCase(caseId) {
  return requestJson(`/cases/${caseId}/analyze`, { method: 'POST' })
}

export async function fetchDocumentTypes() {
  return requestJson('/metadata/document-types')
}

export async function uploadCase(formData) {
  return requestJson('/upload', {
    method: 'POST',
    body: formData,
  })
}
