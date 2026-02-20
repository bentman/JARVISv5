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
  }
}

export async function getHealth() {
  const response = await fetch(`${API_BASE_URL}/health`)

  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`)
  }

  return response.json()
}