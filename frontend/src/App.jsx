import { useEffect, useRef, useState } from 'react'
import ReactMarkdown from 'react-markdown'
import { createOrContinueTask, getDetailedHealth, getHealth } from './api/taskClient'
import SettingsPanel from './components/SettingsPanel'
import WorkflowVisualizer from './components/WorkflowVisualizer'

function renderAssistantContent(content) {
  return (
    <div
      style={{
        whiteSpace: 'pre-wrap',
        overflowWrap: 'anywhere',
      }}
    >
      <ReactMarkdown
        components={{
          pre({ children }) {
            return (
              <pre
                style={{
                  margin: '8px 0',
                  padding: '10px',
                  borderRadius: 10,
                  background: '#050810',
                  border: '1px solid #00d4ff80',
                  boxShadow: '0 0 10px #00d4ff33',
                  whiteSpace: 'pre-wrap',
                  overflowWrap: 'anywhere',
                }}
              >
                {children}
              </pre>
            )
          },
          code({ inline, className, children, ...props }) {
            if (inline) {
              return (
                <code
                  className={className}
                  style={{
                    fontFamily: 'Consolas, Monaco, monospace',
                    background: '#050810',
                    border: '1px solid #00d4ff55',
                    borderRadius: 6,
                    padding: '1px 4px',
                  }}
                  {...props}
                >
                  {children}
                </code>
              )
            }

            return (
              <code
                className={className}
                style={{
                  fontFamily: 'Consolas, Monaco, monospace',
                }}
                {...props}
              >
                {children}
              </code>
            )
          },
        }}
      >
        {String(content ?? '')}
      </ReactMarkdown>
    </div>
  )
}

function App() {
  const [messages, setMessages] = useState([])
  const [taskId, setTaskId] = useState(null)
  const [finalState, setFinalState] = useState(null)
  const [isBackendOnline, setIsBackendOnline] = useState(false)
  const [detailedHealth, setDetailedHealth] = useState(null)
  const [isDetailedDiagnosticsUnavailable, setIsDetailedDiagnosticsUnavailable] = useState(false)
  const [isSettingsOpen, setIsSettingsOpen] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [input, setInput] = useState('')
  const inputRef = useRef(null)
  const messagesEndRef = useRef(null)
  const shortTaskId = taskId ? taskId.replace(/^task-/, '').slice(-8) : ''

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'auto' })
  }, [messages])

  useEffect(() => {
    let isMounted = true

    const checkHealth = async () => {
      try {
        await getHealth()
        if (isMounted) {
          setIsBackendOnline(true)
        }
      } catch {
        if (isMounted) {
          setIsBackendOnline(false)
        }
      }
    }

    checkHealth()
    const intervalId = setInterval(checkHealth, 5000)

    return () => {
      isMounted = false
      clearInterval(intervalId)
    }
  }, [])

  useEffect(() => {
    let isMounted = true

    const checkDetailedHealth = async () => {
      try {
        const data = await getDetailedHealth()
        if (isMounted) {
          setDetailedHealth(data)
          setIsDetailedDiagnosticsUnavailable(false)
        }
      } catch {
        if (isMounted) {
          setIsDetailedDiagnosticsUnavailable(true)
        }
      }
    }

    checkDetailedHealth()
    const intervalId = setInterval(checkDetailedHealth, 30000)

    return () => {
      isMounted = false
      clearInterval(intervalId)
    }
  }, [])

  const modelIndicator = detailedHealth?.model?.selected || 'unknown'
  const cache = detailedHealth?.cache
  const cacheIndicator = !cache
    ? 'unknown'
    : cache.enabled === false
      ? 'disabled'
      : cache.connected === true
        ? 'enabled / connected'
        : 'enabled / disconnected'

  const handleSend = async () => {
    const userInput = input.trim()
    if (!userInput || isLoading) {
      return
    }

    setMessages((prev) => [...prev, { role: 'user', content: userInput }])
    setIsLoading(true)

    try {
      const response = await createOrContinueTask({
        user_input: userInput,
        task_id: taskId || undefined,
      })

      const assistantContent = String(response.llm_output || 'No response text received.')

      setTaskId(response.task_id)
      setFinalState(response.final_state)
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: assistantContent,
          failure: response.failure ?? null,
        },
      ])
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        {
          role: 'error',
          content: err instanceof Error ? err.message : 'Request failed',
        },
      ])
    } finally {
      setIsLoading(false)
      setInput('')
      inputRef.current?.focus()
    }
  }

  const handleNewChat = () => {
    setMessages([])
    setTaskId(null)
    setFinalState(null)
    setInput('')
    inputRef.current?.focus()
  }

  const handleInputKeyDown = (event) => {
    if (event.key === 'Enter') {
      handleSend()
    }
  }

  return (
    <div
      style={{
        height: '100vh',
        display: 'flex',
        flexDirection: 'column',
        fontFamily: 'Arial, sans-serif',
        background: '#050810',
        color: '#e5f6ff',
      }}
    >
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          padding: '14px 18px',
          borderBottom: '1px solid #00d4ff33',
          flexShrink: 0,
          background: '#0a0e1a',
          boxShadow: '0 0 16px #00d4ff1f',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
          <div style={{ fontSize: 32, fontWeight: 700 }}>JARVISv5</div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 14, color: '#b8deeb' }}>
            <span
              style={{
                width: 10,
                height: 10,
                borderRadius: '50%',
                background: isBackendOnline ? '#10b981' : '#ef4444',
                boxShadow: isBackendOnline ? '0 0 8px #10b98199' : 'none',
                display: 'inline-block',
              }}
            />
            {isBackendOnline ? 'Online' : 'Offline'}
            <span style={{ opacity: 0.6 }}>|</span>
            <span>Task: {shortTaskId || '—'}</span>
            <span style={{ opacity: 0.6 }}>|</span>
            <span>State: {finalState || '—'}</span>
            <span style={{ opacity: 0.6 }}>|</span>
            <span>
              Model:{' '}
              <span
                title={modelIndicator}
                style={{
                  display: 'inline-block',
                  maxWidth: 220,
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                  whiteSpace: 'nowrap',
                  verticalAlign: 'bottom',
                }}
              >
                {modelIndicator}
              </span>
            </span>
            <span style={{ opacity: 0.6 }}>|</span>
            <span>Cache: {cacheIndicator}</span>
            {isDetailedDiagnosticsUnavailable ? (
              <>
                <span style={{ opacity: 0.6 }}>|</span>
                <span style={{ color: '#f59e0b' }}>Diagnostics unavailable</span>
              </>
            ) : null}
          </div>
          <button
            type="button"
            onClick={() => setIsSettingsOpen(true)}
            style={{
              border: '1px solid #00d4ff80',
              background: '#1a2332',
              color: '#00d4ff',
              padding: '8px 12px',
              borderRadius: 10,
              cursor: 'pointer',
            }}
          >
            Settings
          </button>
          <button
            type="button"
            onClick={handleNewChat}
            style={{
              border: '1px solid #00d4ff80',
              background: '#1a2332',
              color: '#00d4ff',
              padding: '8px 12px',
              borderRadius: 10,
              cursor: 'pointer',
            }}
          >
            New Chat
          </button>
        </div>

        <div />
      </div>

      <SettingsPanel isOpen={isSettingsOpen} onClose={() => setIsSettingsOpen(false)} />

      <div
        style={{
          flex: 1,
          overflowY: 'auto',
          padding: 16,
          background: '#050810',
        }}
      >
        {messages.length === 0 ? <div style={{ color: '#8fb6c2', fontSize: 18 }}>No messages yet.</div> : null}
        {messages.map((message, index) => {
          const isUser = message.role === 'user'
          const isError = message.role === 'error'
          const rowJustify = isUser ? 'flex-end' : 'flex-start'
          const bubbleBg = isUser ? '#3b82f6' : isError ? '#3a1111' : '#1a2332'
          const bubbleBorder = isUser ? '1px solid #3b82f6' : isError ? '1px solid #ef4444' : '1px solid #00d4ff80'
          const bubbleShadow = isUser ? 'none' : isError ? 'none' : '0 0 10px #00d4ff33'

          return (
            <div key={`${message.role}-${index}`} style={{ display: 'flex', justifyContent: rowJustify, marginBottom: 14 }}>
              <div
                style={{
                  display: 'flex',
                  flexDirection: isUser ? 'row-reverse' : 'row',
                  alignItems: 'flex-end',
                  gap: 10,
                  maxWidth: '85%',
                }}
              >
                <div
                  style={{
                    background: bubbleBg,
                    border: bubbleBorder,
                    boxShadow: bubbleShadow,
                    borderRadius: 20,
                    padding: '12px 14px',
                    fontSize: 18,
                    lineHeight: 1.4,
                    wordBreak: 'break-word',
                  }}
                >
                  {message.role === 'assistant' ? (
                    <>
                      {renderAssistantContent(message.content)}
                      {message.failure ? (
                        <div
                          style={{
                            marginTop: 10,
                            padding: '8px 10px',
                            borderRadius: 10,
                            background: '#0a0e1a',
                            border: '1px solid #ef444466',
                            fontSize: 14,
                            color: '#fca5a5',
                          }}
                        >
                          <div>
                            {(Array.isArray(message.failure.attempted_providers) &&
                            message.failure.attempted_providers.length > 0
                              ? 'Search failed: '
                              : 'Tool failed: ') +
                              String(message.failure.reason || 'unknown error')}
                          </div>
                          {Array.isArray(message.failure.attempted_providers) &&
                          message.failure.attempted_providers.length > 0 ? (
                            <div style={{ marginTop: 4 }}>
                              Attempted: {message.failure.attempted_providers.join(' → ')}
                            </div>
                          ) : null}
                          {message.failure.code ? (
                            <div style={{ marginTop: 4 }}>Code: {String(message.failure.code)}</div>
                          ) : null}
                        </div>
                      ) : null}
                    </>
                  ) : (
                    <pre
                      style={{
                        margin: 0,
                        whiteSpace: 'pre-wrap',
                        overflowWrap: 'anywhere',
                        fontFamily: 'inherit',
                      }}
                    >
                      {message.content}
                    </pre>
                  )}
                </div>
              </div>
            </div>
          )
        })}
        {taskId ? <WorkflowVisualizer taskId={taskId} /> : null}
        <div ref={messagesEndRef} />
      </div>

      <div
        style={{
          display: 'flex',
          gap: 8,
          padding: 12,
          borderTop: '1px solid #00d4ff33',
          flexShrink: 0,
          background: '#1a2332',
        }}
      >
        <input
          ref={inputRef}
          type="text"
          value={input}
          onChange={(event) => setInput(event.target.value)}
          onKeyDown={handleInputKeyDown}
          placeholder="Type a message"
          disabled={isLoading}
          style={{
            flex: 1,
            padding: 10,
            borderRadius: 10,
            border: '1px solid #00d4ff80',
            background: '#0a0e1a',
            color: '#e5f6ff',
            outlineColor: '#00d4ff',
            fontSize: 18,
          }}
        />
        <button
          type="button"
          onClick={handleSend}
          disabled={isLoading || input.trim().length === 0}
          style={{
            padding: '10px 14px',
            borderRadius: 10,
            border: '1px solid #00d4ff',
            background: '#00d4ff',
            color: '#050810',
            fontWeight: 600,
            cursor: isLoading || input.trim().length === 0 ? 'not-allowed' : 'pointer',
          }}
        >
          {isLoading ? 'Sending...' : 'Send'}
        </button>
      </div>
    </div>
  )
}

export default App
