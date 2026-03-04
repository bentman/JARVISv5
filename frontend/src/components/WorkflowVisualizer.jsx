import { useEffect, useState } from 'react'
import { getWorkflow } from '../api/taskClient'

function WorkflowVisualizer({ taskId }) {
  const [workflow, setWorkflow] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [isTelemetryUnavailable, setIsTelemetryUnavailable] = useState(false)

  useEffect(() => {
    if (!taskId) {
      setWorkflow(null)
      setError('')
      setLoading(false)
      setIsTelemetryUnavailable(false)
      return
    }

    setWorkflow(null)
    setError('')
    setIsTelemetryUnavailable(false)

    let isMounted = true

    const refreshWorkflow = async () => {
      if (isMounted) {
        setLoading(true)
      }

      try {
        const data = await getWorkflow(taskId)
        if (isMounted) {
          setWorkflow(data)
          setError('')
          setIsTelemetryUnavailable(false)
        }
      } catch (err) {
        if (isMounted) {
          const message = err instanceof Error ? err.message : 'Failed to load workflow telemetry'
          if (message.includes('404')) {
            setWorkflow(null)
            setError('')
            setIsTelemetryUnavailable(true)
          } else {
            setError(message)
            setIsTelemetryUnavailable(false)
          }
        }
      } finally {
        if (isMounted) {
          setLoading(false)
        }
      }
    }

    refreshWorkflow()
    const intervalId = setInterval(refreshWorkflow, 3000)

    return () => {
      isMounted = false
      clearInterval(intervalId)
    }
  }, [taskId])

  const executionOrder = workflow?.workflow_execution_order ?? []
  const nodeEvents = workflow?.node_events ?? []

  return (
    <div
      style={{
        margin: '12px 16px 0 16px',
        padding: 12,
        border: '1px solid #00d4ff33',
        borderRadius: 10,
        background: '#0a0e1a',
      }}
    >
      <div style={{ fontWeight: 600, marginBottom: 8 }}>Workflow Telemetry</div>

      {loading ? <div style={{ color: '#8fb6c2', marginBottom: 8 }}>Loading workflow...</div> : null}

      {error ? (
        <div style={{ color: '#ef4444', marginBottom: 8 }}>Error: {error}</div>
      ) : null}

      {!loading && !error && !isTelemetryUnavailable && !workflow ? (
        <div style={{ color: '#8fb6c2' }}>No workflow data.</div>
      ) : null}

      {!loading && !error && isTelemetryUnavailable ? (
        <div style={{ color: '#8fb6c2' }}>Workflow telemetry not available yet.</div>
      ) : null}

      {!loading && !error && workflow && executionOrder.length === 0 && nodeEvents.length === 0 ? (
        <div style={{ color: '#8fb6c2' }}>No workflow telemetry available yet.</div>
      ) : null}

      {workflow ? (
        <div style={{ marginBottom: 10 }}>
          <div style={{ fontWeight: 600, marginBottom: 4 }}>Execution Order</div>
          {executionOrder.length > 0 ? (
          <ol style={{ margin: 0, paddingLeft: 20 }}>
            {executionOrder.map((nodeId, index) => (
              <li key={`${nodeId}-${index}`}>{nodeId}</li>
            ))}
          </ol>
          ) : (
            <div style={{ color: '#8fb6c2' }}>None yet.</div>
          )}
        </div>
      ) : null}

      {nodeEvents.length > 0 ? (
        <div>
          <div style={{ fontWeight: 600, marginBottom: 4 }}>Node Events</div>
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 14 }}>
              <thead>
                <tr>
                  <th style={{ textAlign: 'left', borderBottom: '1px solid #00d4ff33', padding: '4px 6px' }}>node_id</th>
                  <th style={{ textAlign: 'left', borderBottom: '1px solid #00d4ff33', padding: '4px 6px' }}>event_type</th>
                  <th style={{ textAlign: 'left', borderBottom: '1px solid #00d4ff33', padding: '4px 6px' }}>success</th>
                  <th style={{ textAlign: 'left', borderBottom: '1px solid #00d4ff33', padding: '4px 6px' }}>start_offset_ns</th>
                  <th style={{ textAlign: 'left', borderBottom: '1px solid #00d4ff33', padding: '4px 6px' }}>elapsed_ns</th>
                  <th style={{ textAlign: 'left', borderBottom: '1px solid #00d4ff33', padding: '4px 6px' }}>error</th>
                </tr>
              </thead>
              <tbody>
                {nodeEvents.map((event, index) => (
                  <tr key={`${event.node_id || 'node'}-${event.event_type || 'event'}-${index}`}>
                    <td style={{ borderBottom: '1px solid #00d4ff22', padding: '4px 6px' }}>{event.node_id || '—'}</td>
                    <td style={{ borderBottom: '1px solid #00d4ff22', padding: '4px 6px' }}>{event.event_type || '—'}</td>
                    <td style={{ borderBottom: '1px solid #00d4ff22', padding: '4px 6px' }}>{String(event.success)}</td>
                    <td style={{ borderBottom: '1px solid #00d4ff22', padding: '4px 6px' }}>
                      {event.start_offset_ns ?? '—'}
                    </td>
                    <td style={{ borderBottom: '1px solid #00d4ff22', padding: '4px 6px' }}>{event.elapsed_ns ?? '—'}</td>
                    <td style={{ borderBottom: '1px solid #00d4ff22', padding: '4px 6px', color: '#fca5a5' }}>
                      {event.error || '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ) : null}
    </div>
  )
}

export default WorkflowVisualizer
