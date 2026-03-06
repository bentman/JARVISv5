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