import { useState } from 'react'
import { searchMemory } from '../api/taskClient'

function toSnippet(text, maxLength = 180) {
  const normalized = String(text || '').replace(/\s+/g, ' ').trim()
  if (normalized.length <= maxLength) {
    return normalized
  }
  return `${normalized.slice(0, maxLength)}...`
}

function MemoryPanel({ isOpen, onClose, onReferenceResult }) {
  const [query, setQuery] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [results, setResults] = useState([])

  if (!isOpen) {
    return null
  }

  const handleSearch = async () => {
    const trimmed = query.trim()
    if (!trimmed) {
      setError('Enter a query to search memory.')
      setResults([])
      return
    }

    setLoading(true)
    setError('')

    try {
      const response = await searchMemory(trimmed, 10)
      const semantic = Array.isArray(response?.semantic_results) ? response.semantic_results : []
      const episodic = Array.isArray(response?.episodic_results) ? response.episodic_results : []
      setResults([...semantic, ...episodic])
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to search memory')
      setResults([])
    } finally {
      setLoading(false)
    }
  }

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
        <div style={{ fontWeight: 700, fontSize: 18 }}>Memory Search</div>
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

      <div style={{ display: 'flex', gap: 8, marginBottom: 10 }}>
        <input
          type="text"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === 'Enter') {
              event.preventDefault()
              handleSearch()
            }
          }}
          placeholder="Search memory"
          style={{
            flex: 1,
            padding: '8px 10px',
            borderRadius: 8,
            border: '1px solid #00d4ff33',
            background: '#111827',
            color: '#dbeafe',
          }}
        />
        <button
          type="button"
          onClick={handleSearch}
          disabled={loading}
          style={{
            border: '1px solid #00d4ff80',
            background: '#1a2332',
            color: '#00d4ff',
            padding: '6px 10px',
            borderRadius: 8,
            cursor: loading ? 'not-allowed' : 'pointer',
            opacity: loading ? 0.6 : 1,
          }}
        >
          Search
        </button>
      </div>

      {loading ? <div style={{ color: '#8fb6c2', marginBottom: 8 }}>Searching...</div> : null}
      {error ? <div style={{ color: '#ef4444', marginBottom: 8 }}>{error}</div> : null}
      {!loading && !error && results.length === 0 ? <div style={{ color: '#8fb6c2' }}>No results.</div> : null}

      {results.map((result, index) => {
        const source = String(result?.source || 'unknown')
        const content = String(result?.content || '')
        const snippet = toSnippet(content)
        const timestamp = result?.metadata?.timestamp ? String(result.metadata.timestamp) : '—'

        return (
          <div
            key={`${source}-${index}`}
            style={{
              border: '1px solid #00d4ff22',
              borderRadius: 8,
              padding: 10,
              marginBottom: 10,
              background: '#111827',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', gap: 8, marginBottom: 6 }}>
              <span style={{ color: '#00d4ff', fontWeight: 600 }}>{source}</span>
              <span style={{ color: '#8fb6c2', fontSize: 12 }}>{timestamp}</span>
            </div>
            <div style={{ color: '#dbeafe', marginBottom: 8, whiteSpace: 'pre-wrap' }}>
              {snippet || '—'}
            </div>
            <button
              type="button"
              onClick={() => onReferenceResult?.({ source, snippet })}
              style={{
                border: '1px solid #00d4ff80',
                background: '#1a2332',
                color: '#00d4ff',
                padding: '4px 8px',
                borderRadius: 6,
                cursor: 'pointer',
              }}
            >
              Reference
            </button>
          </div>
        )
      })}
    </div>
  )
}

export default MemoryPanel