import { useEffect, useState } from 'react'

function App() {
  const [health, setHealth] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    const loadHealth = async () => {
      try {
        const response = await fetch('http://localhost:8000/health')
        if (!response.ok) {
          throw new Error(`HTTP ${response.status}`)
        }
        const data = await response.json()
        setHealth(data)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Request failed')
      }
    }

    loadHealth()
  }, [])

  if (error) {
    return <div>Error: {error}</div>
  }

  if (!health) {
    return <div>Loading backend health...</div>
  }

  return (
    <div>
      Service: {health.service} | Status: {health.status}
    </div>
  )
}

export default App
