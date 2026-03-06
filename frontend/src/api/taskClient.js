const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export async function createOrContinueTask({ user_input, task_id }) {
  const body = task_id ? { user_input, task_id } : { user_input }

  const response = await fetch(`${API_BASE_URL}/task`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(body),
  })

  if (!response.ok) {
    const errorText = await response.text()
    throw new Error(`HTTP ${response.status}: ${errorText}`)
  }

  const data = await response.json()

  return {
    task_id: data.task_id,
    final_state: data.final_state,
    llm_output: data.llm_output,
    failure: data.failure,
  }
}

export async function createOrContinueTaskUpload({ user_input, task_id, file }) {
  const form = new FormData()
  form.append('user_input', String(user_input || ''))
  if (task_id) {
    form.append('task_id', String(task_id))
  }
  if (file) {
    form.append('file', file)
  }

  const response = await fetch(`${API_BASE_URL}/task/upload`, {
    method: 'POST',
    body: form,
  })

  if (!response.ok) {
    const errorText = await response.text()
    throw new Error(`HTTP ${response.status}: ${errorText}`)
  }

  const data = await response.json()
  return {
    task_id: data.task_id,
    final_state: data.final_state,
    llm_output: data.llm_output,
    failure: data.failure,
    attachment: data.attachment ?? null,
  }
}

function parseSseLines(rawText) {
  const lines = rawText.split('\n')
  let eventName = 'message'
  const dataLines = []

  for (const line of lines) {
    if (line.startsWith('event:')) {
      eventName = line.slice('event:'.length).trim()
      continue
    }
    if (line.startsWith('data:')) {
      dataLines.push(line.slice('data:'.length).trim())
    }
  }

  let payload = {}
  const dataText = dataLines.join('\n')
  if (dataText) {
    payload = JSON.parse(dataText)
  }

  return { event: eventName, payload }
}

export async function createOrContinueTaskStream({
  user_input,
  task_id,
  onChunk,
  onDone,
  onError,
}) {
  const body = task_id ? { user_input, task_id } : { user_input }

  const response = await fetch(`${API_BASE_URL}/task/stream`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(body),
  })

  if (!response.ok) {
    const errorText = await response.text()
    throw new Error(`HTTP ${response.status}: ${errorText}`)
  }

  if (!response.body) {
    throw new Error('Streaming response body unavailable')
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { value, done } = await reader.read()
    if (done) {
      break
    }

    buffer += decoder.decode(value, { stream: true })
    const frames = buffer.split('\n\n')
    buffer = frames.pop() || ''

    for (const frame of frames) {
      const trimmed = frame.trim()
      if (!trimmed) {
        continue
      }

      const { event, payload } = parseSseLines(trimmed)
      if (event === 'chunk') {
        onChunk?.(String(payload.chunk || ''))
      } else if (event === 'done') {
        onDone?.({
          task_id: payload?.task_id,
          final_state: payload?.final_state,
          llm_output: payload?.llm_output,
          failure: payload?.failure,
          tool_preview: payload?.tool_preview ?? null,
        })
      } else if (event === 'error') {
        onError?.(String(payload.error || 'stream_error'))
      }
    }
  }
}

export async function getHealth() {
  const response = await fetch(`${API_BASE_URL}/health`)

  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`)
  }

  return response.json()
}

export async function getSettings() {
  const response = await fetch(`${API_BASE_URL}/settings`)

  if (!response.ok) {
    throw new Error(`GET /settings failed: ${response.status}`)
  }

  return response.json()
}

function parseHeaderList(value) {
  if (!value) {
    return []
  }

  return value
    .split(',')
    .map((item) => item.trim())
    .filter(Boolean)
}

export async function updateSettings(updates) {
  const response = await fetch(`${API_BASE_URL}/settings`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(updates),
  })

  if (!response.ok) {
    const errorText = await response.text()
    throw new Error(`POST /settings failed: ${response.status} ${errorText}`)
  }

  const settings = await response.json()
  const restartRequired = response.headers.get('X-Settings-Restart-Required') === 'true'
  const restartRequiredFields = parseHeaderList(response.headers.get('X-Settings-Restart-Required-Fields'))
  const hotAppliedFields = parseHeaderList(response.headers.get('X-Settings-Hot-Applied-Fields'))

  return {
    settings,
    restartRequired,
    restartRequiredFields,
    hotAppliedFields,
  }
}

export async function getBudget() {
  const response = await fetch(`${API_BASE_URL}/budget`)

  if (!response.ok) {
    throw new Error(`GET /budget failed: ${response.status}`)
  }

  return response.json()
}

export async function updateBudgetLimits(updates) {
  const response = await fetch(`${API_BASE_URL}/budget`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(updates),
  })

  if (!response.ok) {
    const errorText = await response.text()
    throw new Error(`POST /budget failed: ${response.status} ${errorText}`)
  }

  return response.json()
}

export async function getDetailedHealth() {
  const response = await fetch(`${API_BASE_URL}/health/detailed`)

  if (!response.ok) {
    throw new Error(`GET /health/detailed failed: ${response.status}`)
  }

  return response.json()
}

export async function getReadyHealth() {
  const response = await fetch(`${API_BASE_URL}/health/ready`)

  if (!response.ok) {
    throw new Error(`GET /health/ready failed: ${response.status}`)
  }

  return response.json()
}

export async function getWorkflow(taskId) {
  const response = await fetch(`${API_BASE_URL}/workflow/${encodeURIComponent(taskId)}`)

  if (!response.ok) {
    throw new Error(`GET /workflow/{task_id} failed: ${response.status}`)
  }

  return response.json()
}