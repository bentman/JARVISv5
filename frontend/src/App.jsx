import { useState } from 'react'
import useChatState from './state/useChatState'
import { appStyles, colors, getSendButtonStyle } from './styles/theme'
import { renderChatMessage } from './utils/renderHelpers'
import SettingsPanel from './components/SettingsPanel'
import WorkflowVisualizer from './components/WorkflowVisualizer'
import MemoryPanel from './components/MemoryPanel'

function App() {
  const [isMemoryOpen, setIsMemoryOpen] = useState(false)

  const {
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
  } = useChatState()

  const isSendDisabled = isLoading || input.trim().length === 0

  return (
    <div style={appStyles.container}>
      <div style={appStyles.header}>
        <div style={appStyles.headerLeft}>
          <div style={appStyles.title}>JARVISv5</div>
          <div style={appStyles.statusRow}>
            <span
              style={{
                width: 10,
                height: 10,
                borderRadius: '50%',
                background: isBackendOnline ? colors.success : colors.danger,
                boxShadow: isBackendOnline ? '0 0 8px #10b98199' : 'none',
                display: 'inline-block',
              }}
            />
            {isBackendOnline ? 'Online' : 'Offline'}
            <span style={appStyles.divider}>|</span>
            <span>Task: {shortTaskId || '—'}</span>
            <span style={appStyles.divider}>|</span>
            <span>State: {finalState || '—'}</span>
            <span style={appStyles.divider}>|</span>
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
            <span style={appStyles.divider}>|</span>
            <span>Cache: {cacheIndicator}</span>
            {isDetailedDiagnosticsUnavailable ? (
              <>
                <span style={appStyles.divider}>|</span>
                <span style={{ color: colors.warning }}>Diagnostics unavailable</span>
              </>
            ) : null}
          </div>
          <button type="button" onClick={() => setIsMemoryOpen(true)} style={appStyles.headerButton}>Memory</button>
          <button type="button" onClick={() => setIsSettingsOpen(true)} style={appStyles.headerButton}>Settings</button>
          <button type="button" onClick={handleNewChat} style={appStyles.headerButton}>New Chat</button>
        </div>
        <div />
      </div>

      <MemoryPanel
        isOpen={isMemoryOpen}
        onClose={() => setIsMemoryOpen(false)}
        onReferenceResult={({ source, snippet }) => {
          const reference = `[memory:${source}] ${snippet}`.trim()
          setInput((previous) => {
            const current = String(previous || '')
            if (!current.trim()) {
              return reference
            }
            return `${current}\n${reference}`
          })
          inputRef.current?.focus()
        }}
      />

      <SettingsPanel isOpen={isSettingsOpen} onClose={() => setIsSettingsOpen(false)} />

      <div style={appStyles.messagesContainer}>
        {messages.length === 0 ? <div style={appStyles.emptyState}>No messages yet.</div> : null}
        {messages.map((message, index) => renderChatMessage(message, index))}
        {taskId ? <WorkflowVisualizer taskId={taskId} /> : null}
        <div ref={messagesEndRef} />
      </div>

      <div style={appStyles.composer}>
        <input
          ref={fileInputRef}
          type="file"
          accept=".txt,.md,.pdf"
          disabled={isLoading}
          onChange={(event) => {
            const next = event.target.files && event.target.files[0] ? event.target.files[0] : null
            setSelectedFile(next)
          }}
          style={appStyles.fileInput}
        />
        <input
          ref={inputRef}
          type="text"
          value={input}
          onChange={(event) => setInput(event.target.value)}
          onKeyDown={handleInputKeyDown}
          placeholder="Type a message"
          disabled={isLoading}
          style={appStyles.textInput}
        />
        <button
          type="button"
          onClick={handleSend}
          disabled={isSendDisabled}
          style={getSendButtonStyle(isSendDisabled)}
        >
          {isLoading ? 'Sending...' : selectedFile ? 'Send with file' : 'Send'}
        </button>
      </div>
    </div>
  )
}

export default App
