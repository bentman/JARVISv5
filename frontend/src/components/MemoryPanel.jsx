import { useState } from 'react'
import { deleteMemoryEntry, searchMemory } from '../api/taskClient'

function toSnippet(text, maxLength = 180) {
  const normalized = String(text || '').replace(/\s+/g, ' ').trim()
  if (normalized.length <= maxLength) {
    return normalized
  }
  return `${normalized.slice(0, maxLength)}...`
}

function getResultKey(result, index) {
  const source = String(result?.source || 'unknown')
  const semanticId = result?.metadata?.id
  if (source === 'semantic' && semanticId !== null && semanticId !== undefined) {
    return `semantic-${String(semanticId)}`
  }
  const timestamp = result?.metadata?.timestamp ? String(result.metadata.timestamp) : 'na'
  return `${source}-${timestamp}-${index}`
}

function MemoryPanel({ isOpen, onClose, onReferenceResult, isDocked = false }) {
  const [query, setQuery] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [results, setResults] = useState([])
  const [sourceFilter, setSourceFilter] = useState('all')
  const [deleteErrors, setDeleteErrors] = useState({})
  const [deletingKeys, setDeletingKeys] = useState({})
  const [deleteNotice, setDeleteNotice] = useState('')

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
    setDeleteErrors({})
    setDeleteNotice('')

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

  const handleDeleteSemanticEntry = async (result, index) => {
    const source = String(result?.source || '')
    const entryIdRaw = result?.metadata?.id
    if (source !== 'semantic' || entryIdRaw === null || entryIdRaw === undefined) {
      return
    }

    const entryId = Number(entryIdRaw)
    if (!Number.isFinite(entryId)) {
      return
    }

    const key = getResultKey(result, index)
    setDeletingKeys((prev) => ({ ...prev, [key]: true }))
    setDeleteErrors((prev) => ({ ...prev, [key]: '' }))

    try {
      await deleteMemoryEntry(entryId)
      setResults((prev) => prev.filter((item, itemIndex) => getResultKey(item, itemIndex) !== key))
      setDeleteNotice(`Deleted semantic entry ${entryId}.`)
      setTimeout(() => {
        setDeleteNotice('')
      }, 2500)
    } catch (err) {
      setDeleteErrors((prev) => ({
        ...prev,
        [key]: err instanceof Error ? err.message : 'Delete failed',
      }))
    } finally {
      setDeletingKeys((prev) => ({ ...prev, [key]: false }))
    }
  }

  const filteredResults = results.filter((result) => {
    const source = String(result?.source || '')
    if (sourceFilter === 'semantic') {
      return source === 'semantic'
    }
    if (sourceFilter === 'episodic') {
      return source === 'episodic'
    }
    return true
  })

  const containerStyle = isDocked
    ? {
        position: 'relative',
        width: '100%',
        height: '100%',
        background: '#0a0e1a',
        padding: 14,
        overflowY: 'auto',
      }
    : {
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
      }

  return (
    <div style={containerStyle}>
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
      {deleteNotice ? <div style={{ color: '#22c55e', marginBottom: 8 }}>{deleteNotice}</div> : null}

      <div style={{ display: 'flex', gap: 8, marginBottom: 10 }}>
        {[
          { id: 'all', label: 'All' },
          { id: 'semantic', label: 'Semantic' },
          { id: 'episodic', label: 'Episodic' },
        ].map((option) => {
          const active = sourceFilter === option.id
          return (
            <button
              key={option.id}
              type="button"
              onClick={() => setSourceFilter(option.id)}
              style={{
                border: '1px solid #00d4ff80',
                background: active ? '#113046' : '#1a2332',
                color: '#00d4ff',
                padding: '4px 8px',
                borderRadius: 6,
                cursor: 'pointer',
                fontSize: 12,
              }}
            >
              {option.label}
            </button>
          )
        })}
      </div>

      {!loading && !error && filteredResults.length === 0 ? <div style={{ color: '#8fb6c2' }}>No results.</div> : null}

      {filteredResults.map((result, index) => {
        const source = String(result?.source || 'unknown')
        const content = String(result?.content || '')
        const snippet = toSnippet(content)
        const timestamp = result?.metadata?.timestamp ? String(result.metadata.timestamp) : '—'
        const score = typeof result?.score === 'number' ? result.score.toFixed(3) : '—'
        const semanticId = result?.metadata?.id
        const canDelete = source === 'semantic' && semanticId !== null && semanticId !== undefined
        const key = getResultKey(result, index)
        const deleteError = deleteErrors[key] || ''
        const isDeleting = Boolean(deletingKeys[key])

        return (
          <div
            key={key}
            style={{
              border: '1px solid #00d4ff22',
              borderRadius: 8,
              padding: 10,
              marginBottom: 10,
              background: '#111827',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', gap: 8, marginBottom: 6 }}>
              <span style={{ color: '#00d4ff', fontWeight: 600 }}>
                {source} &nbsp; {score}
              </span>
              <span style={{ color: '#8fb6c2', fontSize: 12 }}>{timestamp}</span>
            </div>
            <div style={{ color: '#dbeafe', marginBottom: 8, whiteSpace: 'pre-wrap' }}>
              {snippet || '—'}
            </div>
            <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
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
              {canDelete ? (
                <button
                  type="button"
                  onClick={() => handleDeleteSemanticEntry(result, index)}
                  disabled={isDeleting}
                  style={{
                    border: '1px solid #ef444480',
                    background: '#2a1a1a',
                    color: '#ef4444',
                    padding: '4px 8px',
                    borderRadius: 6,
                    cursor: isDeleting ? 'not-allowed' : 'pointer',
                    opacity: isDeleting ? 0.7 : 1,
                  }}
                >
                  {isDeleting ? 'Deleting...' : 'Delete'}
                </button>
              ) : null}
            </div>
            {deleteError ? <div style={{ color: '#ef4444', marginTop: 8, fontSize: 12 }}>{deleteError}</div> : null}
          </div>
        )
      })}
    </div>
  )
}

export default MemoryPanel