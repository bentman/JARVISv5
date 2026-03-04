import { useEffect, useState } from 'react'
import { getBudget, getSettings } from '../api/taskClient'

function formatLabel(key) {
  return String(key)
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (char) => char.toUpperCase())
}

function renderObjectRows(data) {
  const entries = Object.entries(data || {}).sort(([a], [b]) => a.localeCompare(b))

  if (entries.length === 0) {
    return <div style={{ color: '#8fb6c2' }}>N/A</div>
  }

  return entries.map(([key, value]) => (
    <div key={key} style={{ marginBottom: 6 }}>
      <span style={{ color: '#8fb6c2' }}>{formatLabel(key)}:</span>{' '}
      <span>{typeof value === 'object' && value !== null ? JSON.stringify(value) : String(value)}</span>
    </div>
  ))
}

function SettingsPanel({ isOpen, onClose }) {
  const [settings, setSettings] = useState(null)
  const [budget, setBudget] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!isOpen) {
      return
    }

    let isMounted = true

    const fetchSettings = async () => {
      if (isMounted) {
        setLoading(true)
      }

      try {
        const [settingsData, budgetData] = await Promise.all([getSettings(), getBudget()])
        if (isMounted) {
          setSettings(settingsData)
          setBudget(budgetData)
          setError('')
        }
      } catch (err) {
        if (isMounted) {
          setError(err instanceof Error ? err.message : 'Failed to load settings panel data')
        }
      } finally {
        if (isMounted) {
          setLoading(false)
        }
      }
    }

    fetchSettings()
    const intervalId = setInterval(fetchSettings, 10000)

    return () => {
      isMounted = false
      clearInterval(intervalId)
    }
  }, [isOpen])

  if (!isOpen) {
    return null
  }

  const hasContent = Boolean(settings) || Boolean(budget)

  return (
    <div
      style={{
        position: 'fixed',
        top: 0,
        right: 0,
        width: 380,
        maxWidth: '100vw',
        height: '100vh',
        background: '#0a0e1a',
        borderLeft: '1px solid #00d4ff33',
        boxShadow: '-8px 0 20px #00000055',
        padding: 14,
        overflowY: 'auto',
        zIndex: 1000,
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
        <div style={{ fontWeight: 700, fontSize: 18 }}>Settings & Budget</div>
        <button
          type="button"
          onClick={onClose}
          style={{
            border: '1px solid #00d4ff80',
            background: '#1a2332',
            color: '#00d4ff',
            padding: '6px 10px',
            borderRadius: 8,
            cursor: 'pointer',
          }}
        >
          Close
        </button>
      </div>

      {loading ? <div style={{ color: '#8fb6c2', marginBottom: 8 }}>Loading panel data...</div> : null}
      {error ? <div style={{ color: '#ef4444', marginBottom: 8 }}>Error: {error}</div> : null}
      {!loading && !error && !hasContent ? <div style={{ color: '#8fb6c2' }}>No settings or budget data.</div> : null}

      {settings ? (
        <div style={{ marginBottom: 14 }}>
          <div style={{ fontWeight: 600, marginBottom: 6 }}>Settings</div>
          {renderObjectRows(settings)}
        </div>
      ) : null}

      {budget ? (
        <div>
          <div style={{ fontWeight: 600, marginBottom: 6 }}>Budget</div>

          <div style={{ marginBottom: 10 }}>
            <div style={{ fontWeight: 600, color: '#8fb6c2', marginBottom: 4 }}>Daily</div>
            {renderObjectRows(budget.daily || {})}
          </div>

          <div>
            <div style={{ fontWeight: 600, color: '#8fb6c2', marginBottom: 4 }}>Monthly</div>
            {budget.monthly == null ? <div style={{ color: '#8fb6c2' }}>N/A</div> : renderObjectRows(budget.monthly)}
          </div>
        </div>
      ) : null}
    </div>
  )
}

export default SettingsPanel
