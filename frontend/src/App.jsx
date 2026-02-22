import { useEffect, useRef, useState } from 'react'
import { createOrContinueTask, getHealth } from './api/taskClient'

function renderAssistantContent(content) {
  const parts = String(content ?? '').split('```')

  return parts.map((part, index) => {
    const isCodeBlock = index % 2 === 1

    if (!isCodeBlock) {
      return (
        <div
          key={`text-${index}`}
          style={{
            whiteSpace: 'pre-wrap',
            overflowWrap: 'anywhere',
          }}
        >
          {part}
        </div>
      )
    }

    const lines = part.split('\n')
    const firstLine = lines[0] ?? ''
    const hasLanguageTag = /^[a-zA-Z0-9_+-]+$/.test(firstLine.trim())
    const codeContent = hasLanguageTag ? lines.slice(1).join('\n') : part

    return (
      <pre
        key={`code-${index}`}
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
        <code style={{ fontFamily: 'Consolas, Monaco, monospace' }}>{codeContent}</code>
      </pre>
    )
  })
}

function App() {
  const [messages, setMessages] = useState([])
  const [taskId, setTaskId] = useState(null)
  const [finalState, setFinalState] = useState(null)
  const [isBackendOnline, setIsBackendOnline] = useState(false)
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
          </div>
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
                  {message.role === 'assistant' && String(message.content).includes('```') ? (
                    renderAssistantContent(message.content)
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
