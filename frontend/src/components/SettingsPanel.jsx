import { useEffect, useMemo, useRef, useState } from 'react'
import { getBudget, getSettings, updateBudgetLimits, updateSettings } from '../api/taskClient'

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

const EDITABLE_FIELDS = [
  'hardware_profile',
  'log_level',
  'allow_external_search',
  'default_search_provider',
  'cache_enabled',
]

const HARDWARE_PROFILE_OPTIONS = ['light', 'medium', 'heavy', 'test', 'npu-optimized']
const LOG_LEVEL_OPTIONS = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
const DEFAULT_SEARCH_PROVIDER_OPTIONS = ['searxng', 'duckduckgo', 'tavily']

function pickEditableSettings(settings) {
  return {
    hardware_profile: String(settings?.hardware_profile ?? 'medium'),
    log_level: String(settings?.log_level ?? 'INFO'),
    allow_external_search: Boolean(settings?.allow_external_search),
    default_search_provider: String(settings?.default_search_provider ?? 'duckduckgo'),
    cache_enabled: Boolean(settings?.cache_enabled),
  }
}

function editableSettingsEqual(a, b) {
  if (!a || !b) {
    return false
  }

  return EDITABLE_FIELDS.every((field) => a[field] === b[field])
}

function pickBudgetLimits(budget) {
  return {
    daily_limit_usd: String(budget?.daily?.limit_usd ?? 0),
    monthly_limit_usd: String(budget?.monthly?.limit_usd ?? 0),
  }
}

function budgetLimitsEqual(a, b) {
  if (!a || !b) {
    return false
  }

  return a.daily_limit_usd === b.daily_limit_usd && a.monthly_limit_usd === b.monthly_limit_usd
}

function SettingsPanel({ isOpen, onClose }) {
  const [settings, setSettings] = useState(null)
  const [serverEditableSettings, setServerEditableSettings] = useState(null)
  const [draftEditableSettings, setDraftEditableSettings] = useState(null)
  const [budget, setBudget] = useState(null)
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [saveError, setSaveError] = useState('')
  const [saveSuccess, setSaveSuccess] = useState('')
  const [hasServerUpdateWhileDirty, setHasServerUpdateWhileDirty] = useState(false)
  const [restartNotice, setRestartNotice] = useState(null)
  const [serverBudgetLimits, setServerBudgetLimits] = useState(null)
  const [draftBudgetLimits, setDraftBudgetLimits] = useState(null)
  const [budgetSaving, setBudgetSaving] = useState(false)
  const [budgetSaveError, setBudgetSaveError] = useState('')
  const [budgetSaveSuccess, setBudgetSaveSuccess] = useState('')
  const [hasBudgetServerUpdateWhileDirty, setHasBudgetServerUpdateWhileDirty] = useState(false)

  const isDirty = useMemo(
    () => !editableSettingsEqual(serverEditableSettings, draftEditableSettings),
    [serverEditableSettings, draftEditableSettings]
  )

  const isBudgetDirty = useMemo(
    () => !budgetLimitsEqual(serverBudgetLimits, draftBudgetLimits),
    [serverBudgetLimits, draftBudgetLimits]
  )

  const isDirtyRef = useRef(false)
  const savingRef = useRef(false)
  const budgetDirtyRef = useRef(false)
  const budgetSavingRef = useRef(false)

  useEffect(() => {
    isDirtyRef.current = isDirty
  }, [isDirty])

  useEffect(() => {
    savingRef.current = saving
  }, [saving])

  useEffect(() => {
    budgetDirtyRef.current = isBudgetDirty
  }, [isBudgetDirty])

  useEffect(() => {
    budgetSavingRef.current = budgetSaving
  }, [budgetSaving])

  const setDraftField = (field, value) => {
    setDraftEditableSettings((previous) => {
      if (!previous) {
        return previous
      }

      return {
        ...previous,
        [field]: value,
      }
    })
    setSaveError('')
    setSaveSuccess('')
    setRestartNotice(null)
  }

  const handleCancel = () => {
    if (!serverEditableSettings) {
      return
    }

    setDraftEditableSettings(serverEditableSettings)
    setHasServerUpdateWhileDirty(false)
    setSaveError('')
    setSaveSuccess('')
    setRestartNotice(null)
  }

  const handleSave = async () => {
    if (!serverEditableSettings || !draftEditableSettings || !isDirty) {
      return
    }

    const updates = {}
    EDITABLE_FIELDS.forEach((field) => {
      if (draftEditableSettings[field] !== serverEditableSettings[field]) {
        updates[field] = draftEditableSettings[field]
      }
    })

    if (Object.keys(updates).length === 0) {
      return
    }

    setSaving(true)
    setSaveError('')
    setSaveSuccess('')

    try {
      const result = await updateSettings(updates)
      const nextSettings = result.settings
      const nextEditable = pickEditableSettings(nextSettings)

      setSettings(nextSettings)
      setServerEditableSettings(nextEditable)
      setDraftEditableSettings(nextEditable)
      setHasServerUpdateWhileDirty(false)
      setSaveSuccess('Settings saved.')
      setRestartNotice({
        restartRequired: result.restartRequired,
        restartRequiredFields: result.restartRequiredFields,
        hotAppliedFields: result.hotAppliedFields,
      })
    } catch (err) {
      setSaveError(err instanceof Error ? err.message : 'Failed to save settings')
    } finally {
      setSaving(false)
    }
  }

  const setBudgetDraftField = (field, value) => {
    setDraftBudgetLimits((previous) => {
      if (!previous) {
        return previous
      }

      return {
        ...previous,
        [field]: value,
      }
    })
    setBudgetSaveError('')
    setBudgetSaveSuccess('')
  }

  const handleBudgetCancel = () => {
    if (!serverBudgetLimits) {
      return
    }

    setDraftBudgetLimits(serverBudgetLimits)
    setHasBudgetServerUpdateWhileDirty(false)
    setBudgetSaveError('')
    setBudgetSaveSuccess('')
  }

  const handleBudgetSave = async () => {
    if (!serverBudgetLimits || !draftBudgetLimits || !isBudgetDirty) {
      return
    }

    const parsedDaily = Number(draftBudgetLimits.daily_limit_usd)
    const parsedMonthly = Number(draftBudgetLimits.monthly_limit_usd)
    if (!Number.isFinite(parsedDaily) || parsedDaily < 0 || !Number.isFinite(parsedMonthly) || parsedMonthly < 0) {
      setBudgetSaveError('Budget limits must be finite numbers greater than or equal to 0.')
      return
    }

    const updates = {}
    if (draftBudgetLimits.daily_limit_usd !== serverBudgetLimits.daily_limit_usd) {
      updates.daily_limit_usd = parsedDaily
    }
    if (draftBudgetLimits.monthly_limit_usd !== serverBudgetLimits.monthly_limit_usd) {
      updates.monthly_limit_usd = parsedMonthly
    }

    if (Object.keys(updates).length === 0) {
      return
    }

    setBudgetSaving(true)
    setBudgetSaveError('')
    setBudgetSaveSuccess('')

    try {
      const nextBudget = await updateBudgetLimits(updates)
      const nextBudgetLimits = pickBudgetLimits(nextBudget)
      setBudget(nextBudget)
      setServerBudgetLimits(nextBudgetLimits)
      setDraftBudgetLimits(nextBudgetLimits)
      setHasBudgetServerUpdateWhileDirty(false)
      setBudgetSaveSuccess('Budget limits saved.')
    } catch (err) {
      setBudgetSaveError(err instanceof Error ? err.message : 'Failed to save budget limits')
    } finally {
      setBudgetSaving(false)
    }
  }

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
          const editable = pickEditableSettings(settingsData)
          const nextBudgetLimits = pickBudgetLimits(budgetData)
          setSettings(settingsData)
          setBudget(budgetData)

          if (!isDirtyRef.current && !savingRef.current) {
            setServerEditableSettings(editable)
            setDraftEditableSettings(editable)
            setHasServerUpdateWhileDirty(false)
          } else {
            setServerEditableSettings(editable)
            setHasServerUpdateWhileDirty(true)
          }

          if (!budgetDirtyRef.current && !budgetSavingRef.current) {
            setServerBudgetLimits(nextBudgetLimits)
            setDraftBudgetLimits(nextBudgetLimits)
            setHasBudgetServerUpdateWhileDirty(false)
          } else {
            setServerBudgetLimits(nextBudgetLimits)
            setHasBudgetServerUpdateWhileDirty(true)
          }

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
      {saveError ? <div style={{ color: '#ef4444', marginBottom: 8 }}>Save error: {saveError}</div> : null}
      {saveSuccess ? <div style={{ color: '#22c55e', marginBottom: 8 }}>{saveSuccess}</div> : null}
      {saving ? <div style={{ color: '#8fb6c2', marginBottom: 8 }}>Saving settings...</div> : null}
      {budgetSaveError ? <div style={{ color: '#ef4444', marginBottom: 8 }}>Budget save error: {budgetSaveError}</div> : null}
      {budgetSaveSuccess ? <div style={{ color: '#22c55e', marginBottom: 8 }}>{budgetSaveSuccess}</div> : null}
      {budgetSaving ? <div style={{ color: '#8fb6c2', marginBottom: 8 }}>Saving budget limits...</div> : null}
      {!loading && !error && !hasContent ? <div style={{ color: '#8fb6c2' }}>No settings or budget data.</div> : null}

      {draftEditableSettings ? (
        <div style={{ marginBottom: 14 }}>
          <div style={{ fontWeight: 600, marginBottom: 6 }}>Settings (Editable)</div>

          <div style={{ marginBottom: 8 }}>
            <div style={{ color: '#8fb6c2', marginBottom: 4 }}>Hardware Profile</div>
            <select
              value={draftEditableSettings.hardware_profile}
              onChange={(event) => setDraftField('hardware_profile', event.target.value)}
              disabled={saving}
              style={{ width: '100%', padding: '6px 8px', borderRadius: 6 }}
            >
              {HARDWARE_PROFILE_OPTIONS.map((option) => (
                <option key={option} value={option}>
                  {option}
                </option>
              ))}
            </select>
          </div>

          <div style={{ marginBottom: 8 }}>
            <div style={{ color: '#8fb6c2', marginBottom: 4 }}>Log Level</div>
            <select
              value={draftEditableSettings.log_level}
              onChange={(event) => setDraftField('log_level', event.target.value)}
              disabled={saving}
              style={{ width: '100%', padding: '6px 8px', borderRadius: 6 }}
            >
              {LOG_LEVEL_OPTIONS.map((option) => (
                <option key={option} value={option}>
                  {option}
                </option>
              ))}
            </select>
          </div>

          <div style={{ marginBottom: 8 }}>
            <label style={{ color: '#8fb6c2', display: 'flex', alignItems: 'center', gap: 8 }}>
              <input
                type="checkbox"
                checked={Boolean(draftEditableSettings.allow_external_search)}
                onChange={(event) => setDraftField('allow_external_search', event.target.checked)}
                disabled={saving}
              />
              Allow External Search
            </label>
          </div>

          <div style={{ marginBottom: 8 }}>
            <div style={{ color: '#8fb6c2', marginBottom: 4 }}>Default Search Provider</div>
            <select
              value={draftEditableSettings.default_search_provider}
              onChange={(event) => setDraftField('default_search_provider', event.target.value)}
              disabled={saving}
              style={{ width: '100%', padding: '6px 8px', borderRadius: 6 }}
            >
              {DEFAULT_SEARCH_PROVIDER_OPTIONS.map((option) => (
                <option key={option} value={option}>
                  {option}
                </option>
              ))}
            </select>
          </div>

          <div style={{ marginBottom: 10 }}>
            <label style={{ color: '#8fb6c2', display: 'flex', alignItems: 'center', gap: 8 }}>
              <input
                type="checkbox"
                checked={Boolean(draftEditableSettings.cache_enabled)}
                onChange={(event) => setDraftField('cache_enabled', event.target.checked)}
                disabled={saving}
              />
              Cache Enabled
            </label>
          </div>

          {isDirty ? <div style={{ color: '#f59e0b', marginBottom: 8 }}>Unsaved changes</div> : null}

          {hasServerUpdateWhileDirty ? (
            <div style={{ color: '#f59e0b', marginBottom: 8 }}>
              New server values were fetched while edits are unsaved. Save or cancel to reconcile.
            </div>
          ) : null}

          {restartNotice ? (
            restartNotice.restartRequired ? (
              <div style={{ color: '#f59e0b', marginBottom: 8 }}>
                Restart required for: {restartNotice.restartRequiredFields.join(', ') || 'updated fields'}
              </div>
            ) : (
              <div style={{ color: '#22c55e', marginBottom: 8 }}>
                Changes hot-applied{restartNotice.hotAppliedFields.length ? `: ${restartNotice.hotAppliedFields.join(', ')}` : '.'}
              </div>
            )
          ) : null}

          <div style={{ display: 'flex', gap: 8 }}>
            <button
              type="button"
              onClick={handleSave}
              disabled={!isDirty || saving}
              style={{
                border: '1px solid #00d4ff80',
                background: '#1a2332',
                color: '#00d4ff',
                padding: '6px 10px',
                borderRadius: 8,
                cursor: !isDirty || saving ? 'not-allowed' : 'pointer',
                opacity: !isDirty || saving ? 0.6 : 1,
              }}
            >
              Save
            </button>
            <button
              type="button"
              onClick={handleCancel}
              disabled={saving || !serverEditableSettings}
              style={{
                border: '1px solid #00d4ff80',
                background: '#1a2332',
                color: '#00d4ff',
                padding: '6px 10px',
                borderRadius: 8,
                cursor: saving || !serverEditableSettings ? 'not-allowed' : 'pointer',
                opacity: saving || !serverEditableSettings ? 0.6 : 1,
              }}
            >
              Cancel
            </button>
          </div>

          {settings ? (
            <div style={{ marginTop: 12 }}>
              <div style={{ fontWeight: 600, marginBottom: 6 }}>Settings (Current Snapshot)</div>
              {renderObjectRows(settings)}
            </div>
          ) : null}
        </div>
      ) : null}

      {budget ? (
        <div>
          <div style={{ fontWeight: 600, marginBottom: 6 }}>Budget</div>

          {draftBudgetLimits ? (
            <div style={{ marginBottom: 10 }}>
              <div style={{ marginBottom: 8 }}>
                <div style={{ color: '#8fb6c2', marginBottom: 4 }}>Daily Limit (USD)</div>
                <input
                  type="number"
                  min="0"
                  step="0.01"
                  value={draftBudgetLimits.daily_limit_usd}
                  onChange={(event) => setBudgetDraftField('daily_limit_usd', event.target.value)}
                  disabled={budgetSaving}
                  style={{ width: '100%', padding: '6px 8px', borderRadius: 6 }}
                />
              </div>

              <div style={{ marginBottom: 8 }}>
                <div style={{ color: '#8fb6c2', marginBottom: 4 }}>Monthly Limit (USD)</div>
                <input
                  type="number"
                  min="0"
                  step="0.01"
                  value={draftBudgetLimits.monthly_limit_usd}
                  onChange={(event) => setBudgetDraftField('monthly_limit_usd', event.target.value)}
                  disabled={budgetSaving}
                  style={{ width: '100%', padding: '6px 8px', borderRadius: 6 }}
                />
              </div>

              {isBudgetDirty ? <div style={{ color: '#f59e0b', marginBottom: 8 }}>Unsaved budget changes</div> : null}

              {hasBudgetServerUpdateWhileDirty ? (
                <div style={{ color: '#f59e0b', marginBottom: 8 }}>
                  New budget values were fetched while edits are unsaved. Save or cancel to reconcile.
                </div>
              ) : null}

              <div style={{ display: 'flex', gap: 8, marginBottom: 10 }}>
                <button
                  type="button"
                  onClick={handleBudgetSave}
                  disabled={!isBudgetDirty || budgetSaving}
                  style={{
                    border: '1px solid #00d4ff80',
                    background: '#1a2332',
                    color: '#00d4ff',
                    padding: '6px 10px',
                    borderRadius: 8,
                    cursor: !isBudgetDirty || budgetSaving ? 'not-allowed' : 'pointer',
                    opacity: !isBudgetDirty || budgetSaving ? 0.6 : 1,
                  }}
                >
                  Save Budget
                </button>
                <button
                  type="button"
                  onClick={handleBudgetCancel}
                  disabled={budgetSaving || !serverBudgetLimits}
                  style={{
                    border: '1px solid #00d4ff80',
                    background: '#1a2332',
                    color: '#00d4ff',
                    padding: '6px 10px',
                    borderRadius: 8,
                    cursor: budgetSaving || !serverBudgetLimits ? 'not-allowed' : 'pointer',
                    opacity: budgetSaving || !serverBudgetLimits ? 0.6 : 1,
                  }}
                >
                  Cancel
                </button>
              </div>
            </div>
          ) : null}

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
