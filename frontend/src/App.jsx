import { useState } from 'react'
import useChatState from './state/useChatState'
import { appStyles, colors, getSendButtonStyle } from './styles/theme'
import { renderChatMessage } from './utils/renderHelpers'
import SettingsPanel from './components/SettingsPanel'
import WorkflowVisualizer from './components/WorkflowVisualizer'
import MemoryPanel from './components/MemoryPanel'

const PANEL_WIDTH = 420

function App() {
  const [activePanel, setActivePanel] = useState(null)

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
  const isAnyPanelOpen = activePanel !== null

  const openMemoryPanel = () => {
    setActivePanel((prev) => (prev === 'memory' ? null : 'memory'))
    setIsSettingsOpen(false)
  }

  const openWorkflowPanel = () => {
    setActivePanel((prev) => (prev === 'workflow' ? null : 'workflow'))
    setIsSettingsOpen(false)
  }

  const openSettingsPanel = () => {
    setActivePanel((prev) => {
      const next = prev === 'settings' ? null : 'settings'
      setIsSettingsOpen(next === 'settings')
      return next
    })
  }

  const closePanels = () => {
    setActivePanel(null)
    setIsSettingsOpen(false)
  }

  return (
    <div style={appStyles.container}>
      <div style={{ display: 'flex', flex: 1, minHeight: 0 }}>
        <div style={{ display: 'flex', flexDirection: 'column', flex: 1, minWidth: 0 }}>
          <div style={appStyles.header}>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8, width: '100%' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 12 }}>
                <div style={{ ...appStyles.statusRow, gap: 10, flexWrap: 'wrap' }}>
                  <div style={appStyles.title}>JARVISv5</div>
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
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginLeft: 'auto' }}>
                  <button type="button" onClick={handleNewChat} style={appStyles.headerButton}>New Chat</button>
                  <button
                    type="button"
                    onClick={openSettingsPanel}
                    style={{ ...appStyles.headerButton, minWidth: 36, padding: '8px 10px' }}
                    aria-label="Settings"
                    title="Settings"
                  >
                    ⚙
                  </button>
                </div>
              </div>

              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 12 }}>
                <div style={{ ...appStyles.statusRow, gap: 8, flexWrap: 'wrap' }}>
                  <span>Cache: {cacheIndicator}</span>
                  <span style={appStyles.divider}>|</span>
                  <span>Task: {shortTaskId || '—'}</span>
                  <span style={appStyles.divider}>|</span>
                  <span>State: {finalState || '—'}</span>
                  {isDetailedDiagnosticsUnavailable ? (
                    <>
                      <span style={appStyles.divider}>|</span>
                      <span style={{ color: colors.warning }}>Diagnostics unavailable</span>
                    </>
                  ) : null}
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginLeft: 'auto' }}>
                  <button type="button" onClick={openMemoryPanel} style={appStyles.headerButton}>Memory</button>
                  <button type="button" onClick={openWorkflowPanel} style={appStyles.headerButton}>Workflow</button>
                </div>
              </div>
            </div>
          </div>

          <div style={appStyles.messagesContainer}>
            {messages.length === 0 ? <div style={appStyles.emptyState}>No messages yet.</div> : null}
            {messages.map((message, index) => renderChatMessage(message, index))}
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

        {isAnyPanelOpen ? (
          <div
            style={{
              width: PANEL_WIDTH,
              maxWidth: '45vw',
              minWidth: 360,
              borderLeft: '1px solid #00d4ff33',
              background: '#0a0e1a',
              boxShadow: '-8px 0 20px #00000055',
              display: 'flex',
              flexDirection: 'column',
              minHeight: 0,
            }}
          >
            {activePanel === 'memory' ? (
              <MemoryPanel
                isOpen={true}
                isDocked={true}
                onClose={closePanels}
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
            ) : null}

            {activePanel === 'settings' ? (
              <SettingsPanel isOpen={isSettingsOpen} isDocked={true} onClose={closePanels} />
            ) : null}

            {activePanel === 'workflow' ? (
              <div style={{ display: 'flex', flexDirection: 'column', minHeight: 0, height: '100%' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '14px 14px 0 14px' }}>
                  <div style={{ fontWeight: 700, fontSize: 18 }}>Workflow Telemetry</div>
                  <button type="button" onClick={closePanels} style={appStyles.headerButton}>
                    Close
                  </button>
                </div>
                <div style={{ overflowY: 'auto', minHeight: 0, flex: 1 }}>
                  {taskId ? (
                    <WorkflowVisualizer taskId={taskId} />
                  ) : (
                    <div style={{ color: colors.muted, padding: '8px 12px 12px 12px' }}>
                      No active task yet.
                    </div>
                  )}
                </div>
              </div>
            ) : null}
          </div>
        ) : null}
      </div>
    </div>
  )
}

export default App