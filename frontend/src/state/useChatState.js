import { useEffect, useRef, useState } from 'react'
import {
  createOrContinueTaskUpload,
  createOrContinueTaskStream,
  getDetailedHealth,
  getHealth,
} from '../api/taskClient'

export default function useChatState() {
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
  const modelIndicator = detailedHealth?.model?.selected || 'unknown'
  const cache = detailedHealth?.cache
  const cacheIndicator = !cache
    ? 'unknown'
    : cache.enabled === false
      ? 'disabled'
      : cache.connected === true
        ? 'enabled / connected'
        : 'enabled / disconnected'

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'auto' })
  }, [messages])

  useEffect(() => {
    let isMounted = true
    const checkHealth = async () => {
      try {
        await getHealth()
        if (isMounted) setIsBackendOnline(true)
      } catch {
        if (isMounted) setIsBackendOnline(false)
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
        if (isMounted) setIsDetailedDiagnosticsUnavailable(true)
      }
    }
    checkDetailedHealth()
    const intervalId = setInterval(checkDetailedHealth, 30000)
    return () => {
      isMounted = false
      clearInterval(intervalId)
    }
  }, [])

  const handleSend = async () => {
    const userInput = input.trim()
    if (!userInput || isLoading) return

    const streamMessageId = `stream-${Date.now()}`
    setMessages((prev) => [...prev, { role: 'user', content: userInput }])
    setMessages((prev) => [
      ...prev,
      { id: streamMessageId, role: 'assistant', content: '', failure: null, tool_preview: null, streaming: true },
    ])
    setIsLoading(true)

    try {
      if (selectedFile) {
        const payload = await createOrContinueTaskUpload({ user_input: userInput, task_id: taskId || undefined, file: selectedFile })
        const nextTaskId = payload?.task_id ? String(payload.task_id) : taskId
        const nextFinalState = payload?.final_state ? String(payload.final_state) : finalState
        const nextOutput = payload?.llm_output != null ? String(payload.llm_output) : null
        setTaskId(nextTaskId || null)
        setFinalState(nextFinalState || null)
        setMessages((prev) =>
          prev.map((message) => (message.id !== streamMessageId ? message : {
            ...message,
            content: nextOutput !== null ? nextOutput : String(message.content || 'No response text received.'),
            failure: payload?.failure ?? null,
            attachment: payload?.attachment ?? null,
            streaming: false,
          }))
        )
      } else {
        await createOrContinueTaskStream({
          user_input: userInput,
          task_id: taskId || undefined,
          onChunk: (chunk) => {
            setMessages((prev) => prev.map((message) => (message.id === streamMessageId ? { ...message, content: `${String(message.content || '')}${String(chunk || '')}` } : message)))
          },
          onDone: (payload) => {
            const nextTaskId = payload?.task_id ? String(payload.task_id) : taskId
            const nextFinalState = payload?.final_state ? String(payload.final_state) : finalState
            const nextOutput = payload?.llm_output != null ? String(payload.llm_output) : null
            setTaskId(nextTaskId || null)
            setFinalState(nextFinalState || null)
            setMessages((prev) =>
              prev.map((message) => (message.id !== streamMessageId ? message : {
                ...message,
                content: nextOutput !== null ? nextOutput : String(message.content || 'No response text received.'),
                failure: payload?.failure ?? null,
                tool_preview: payload?.tool_preview ?? null,
                attachment: null,
                streaming: false,
              }))
            )
          },
          onError: (errorMessage) => {
            setMessages((prev) =>
              prev.map((message) => (message.id === streamMessageId
                ? { ...message, role: 'error', content: String(errorMessage || 'stream_error'), failure: null, streaming: false }
                : message))
            )
          },
        })
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Request failed'
      setMessages((prev) => {
        const hasStreamingMessage = prev.some((message) => message.id === streamMessageId)
        if (!hasStreamingMessage) return [...prev, { role: 'error', content: errorMessage }]
        return prev.map((message) => (message.id === streamMessageId
          ? { ...message, role: 'error', content: errorMessage, failure: null, streaming: false }
          : message))
      })
    } finally {
      setIsLoading(false)
      setInput('')
      setSelectedFile(null)
      if (fileInputRef.current) fileInputRef.current.value = ''
      inputRef.current?.focus()
    }
  }

  const handleNewChat = () => {
    setMessages([])
    setTaskId(null)
    setFinalState(null)
    setInput('')
    setSelectedFile(null)
    if (fileInputRef.current) fileInputRef.current.value = ''
    inputRef.current?.focus()
  }

  const handleInputKeyDown = (event) => {
    if (event.key === 'Enter') handleSend()
  }

  return {
    messages,
    taskId,
    finalState,
    isBackendOnline,
    isDetailedDiagnosticsUnavailable,
    isSettingsOpen,
    isLoading,
    input,
    selectedFile,
    inputRef,
    fileInputRef,
    messagesEndRef,
    shortTaskId,
    modelIndicator,
    cacheIndicator,
    setIsSettingsOpen,
    setInput,
    setSelectedFile,
    handleSend,
    handleNewChat,
    handleInputKeyDown,
  }
}