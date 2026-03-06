import { useEffect, useRef, useState } from 'react'
import ReactMarkdown from 'react-markdown'
import {
  createOrContinueTaskUpload,
  createOrContinueTaskStream,
  getDetailedHealth,
  getHealth,
} from './api/taskClient'
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

function truncatePreviewText(value, maxLength = 120) {
  const text = String(value ?? '')
  if (text.length <= maxLength) {
    return text
  }
  return `${text.slice(0, maxLength - 1)}…`
}

function normalizePreviewItems(items) {
  if (!Array.isArray(items)) {
    return []
  }
  return items.slice(0, 3)
}

function renderToolPreview(toolPreview) {
  if (!toolPreview || typeof toolPreview !== 'object') {
    return null
  }

  const toolName = String(toolPreview.tool_name || '').toLowerCase()
  if (toolName !== 'search' && toolName !== 'read') {
    return null
  }

  const code = toolPreview.code != null ? String(toolPreview.code) : null
  const reason = toolPreview.reason != null ? String(toolPreview.reason) : null
  const attemptedProviders = Array.isArray(toolPreview.attempted_providers)
    ? toolPreview.attempted_providers.map((value) => String(value))
    : []

  const allItems = Array.isArray(toolPreview.items) ? toolPreview.items : []
  const boundedItems = normalizePreviewItems(allItems)
  const overflowCount = Math.max(0, allItems.length - boundedItems.length)

  const hasMetadata = Boolean(code || reason || attemptedProviders.length > 0)
  const hasItems = boundedItems.length > 0

  if (!hasMetadata && !hasItems) {
    return null
  }

  return (
    <div
      style={{
        marginTop: 10,
        padding: '8px 10px',
        borderRadius: 10,
        background: '#0a0e1a',
        border: '1px solid #00d4ff55',
        fontSize: 14,
        color: '#b8deeb',
      }}
    >
      <div style={{ fontWeight: 600, color: '#00d4ff' }}>
        {toolName === 'search' ? 'Search preview' : 'Read preview'}
      </div>

      {code ? <div style={{ marginTop: 4 }}>Code: {truncatePreviewText(code, 80)}</div> : null}
      {reason ? <div style={{ marginTop: 4 }}>Reason: {truncatePreviewText(reason, 120)}</div> : null}
      {attemptedProviders.length > 0 ? (
        <div style={{ marginTop: 4 }}>
          Attempted: {truncatePreviewText(attemptedProviders.join(' → '), 120)}
        </div>
      ) : null}

      {hasItems ? (
        <div style={{ marginTop: 6 }}>
          {boundedItems.map((item, idx) => {
            const itemObject = item && typeof item === 'object' ? item : {}
            const titleCandidate =
              itemObject.title ?? itemObject.url ?? itemObject.source ?? itemObject.path ?? item
            const detailCandidate =
              itemObject.snippet ?? itemObject.text ?? itemObject.content ?? itemObject.reason

            return (
              <div key={`preview-item-${idx}`} style={{ marginTop: idx === 0 ? 0 : 4 }}>
                <div>{`${idx + 1}. ${truncatePreviewText(titleCandidate, 120)}`}</div>
                {detailCandidate != null ? (
                  <div style={{ opacity: 0.85, fontSize: 13 }}>
                    {truncatePreviewText(detailCandidate, 120)}
                  </div>
                ) : null}
              </div>
            )
          })}
          {overflowCount > 0 ? (
            <div style={{ marginTop: 4, opacity: 0.85 }}>+{overflowCount} more</div>
          ) : null}
        </div>
      ) : null}
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
  const [selectedFile, setSelectedFile] = useState(null)
  const inputRef = useRef(null)
  const fileInputRef = useRef(null)
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

    const streamMessageId = `stream-${Date.now()}`
    setMessages((prev) => [...prev, { role: 'user', content: userInput }])
    setMessages((prev) => [
      ...prev,
      {
        id: streamMessageId,
        role: 'assistant',
        content: '',
        failure: null,
        tool_preview: null,
        streaming: true,
      },
    ])
    setIsLoading(true)

    try {
      if (selectedFile) {
        const payload = await createOrContinueTaskUpload({
          user_input: userInput,
          task_id: taskId || undefined,
          file: selectedFile,
        })
        const nextTaskId = payload?.task_id ? String(payload.task_id) : taskId
        const nextFinalState = payload?.final_state ? String(payload.final_state) : finalState
        const nextOutput = payload?.llm_output != null ? String(payload.llm_output) : null

        setTaskId(nextTaskId || null)
        setFinalState(nextFinalState || null)
        setMessages((prev) =>
          prev.map((message) => {
            if (message.id !== streamMessageId) {
              return message
            }
            return {
              ...message,
              content:
                nextOutput !== null
                  ? nextOutput
                  : String(message.content || 'No response text received.'),
              failure: payload?.failure ?? null,
              attachment: payload?.attachment ?? null,
              streaming: false,
            }
          })
        )
      } else {
        await createOrContinueTaskStream({
          user_input: userInput,
          task_id: taskId || undefined,
          onChunk: (chunk) => {
            setMessages((prev) =>
              prev.map((message) =>
                message.id === streamMessageId
                  ? { ...message, content: `${String(message.content || '')}${String(chunk || '')}` }
                  : message
              )
            )
          },
          onDone: (payload) => {
            const nextTaskId = payload?.task_id ? String(payload.task_id) : taskId
            const nextFinalState = payload?.final_state ? String(payload.final_state) : finalState
            const nextOutput = payload?.llm_output != null ? String(payload.llm_output) : null

            setTaskId(nextTaskId || null)
            setFinalState(nextFinalState || null)
            setMessages((prev) =>
              prev.map((message) => {
                if (message.id !== streamMessageId) {
                  return message
                }
                return {
                  ...message,
                  content:
                    nextOutput !== null
                      ? nextOutput
                      : String(message.content || 'No response text received.'),
                  failure: payload?.failure ?? null,
                  tool_preview: payload?.tool_preview ?? null,
                  attachment: null,
                  streaming: false,
                }
              })
            )
          },
          onError: (errorMessage) => {
            setMessages((prev) =>
              prev.map((message) =>
                message.id === streamMessageId
                  ? {
                      ...message,
                      role: 'error',
                      content: String(errorMessage || 'stream_error'),
                      failure: null,
                      streaming: false,
                    }
                  : message
              )
            )
          },
        })
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Request failed'
      setMessages((prev) => {
        const hasStreamingMessage = prev.some((message) => message.id === streamMessageId)
        if (!hasStreamingMessage) {
          return [...prev, { role: 'error', content: errorMessage }]
        }
        return prev.map((message) =>
          message.id === streamMessageId
            ? {
                ...message,
                role: 'error',
                content: errorMessage,
                failure: null,
                streaming: false,
              }
            : message
        )
      })
    } finally {
      setIsLoading(false)
      setInput('')
      setSelectedFile(null)
      if (fileInputRef.current) {
        fileInputRef.current.value = ''
      }
      inputRef.current?.focus()
    }
  }

  const handleNewChat = () => {
    setMessages([])
    setTaskId(null)
    setFinalState(null)
    setInput('')
    setSelectedFile(null)
    if (fileInputRef.current) {
      fileInputRef.current.value = ''
    }
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
                      {renderToolPreview(message.tool_preview)}
                      {message.attachment ? (
                        <div
                          style={{
                            marginTop: 10,
                            padding: '8px 10px',
                            borderRadius: 10,
                            background: '#0a0e1a',
                            border: '1px solid #00d4ff55',
                            fontSize: 14,
                            color: '#b8deeb',
                          }}
                        >
                          Attachment used: {String(message.attachment.filename || 'unknown')} ({String(message.attachment.mime_type || 'application/octet-stream')}), extracted chars: {Number(message.attachment.extracted_text_length || 0)}
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
          ref={fileInputRef}
          type="file"
          accept=".txt,.md,.pdf"
          disabled={isLoading}
          onChange={(event) => {
            const next = event.target.files && event.target.files[0] ? event.target.files[0] : null
            setSelectedFile(next)
          }}
          style={{
            maxWidth: 220,
            color: '#e5f6ff',
          }}
        />
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
          {isLoading ? 'Sending...' : selectedFile ? 'Send with file' : 'Send'}
        </button>
      </div>
    </div>
  )
}

export default App
