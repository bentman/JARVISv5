import ReactMarkdown from 'react-markdown'
import { colors, radii } from '../styles/theme'

export function renderAssistantContent(content) {
  return (
    <div style={{ whiteSpace: 'pre-wrap', overflowWrap: 'anywhere' }}>
      <ReactMarkdown
        components={{
          pre({ children }) {
            return (
              <pre
                style={{
                  margin: '8px 0',
                  padding: '10px',
                  borderRadius: radii.md,
                  background: colors.appBg,
                  border: `1px solid ${colors.accentBorderStrong}`,
                  boxShadow: `0 0 10px ${colors.accentGlowMid}`,
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
                    background: colors.appBg,
                    border: `1px solid ${colors.accentBorderMid}`,
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
              <code className={className} style={{ fontFamily: 'Consolas, Monaco, monospace' }} {...props}>
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

export function truncatePreviewText(value, maxLength = 120) {
  const text = String(value ?? '')
  if (text.length <= maxLength) return text
  return `${text.slice(0, maxLength - 1)}…`
}

export function normalizePreviewItems(items) {
  if (!Array.isArray(items)) return []
  return items.slice(0, 3)
}

export function renderToolPreview(toolPreview) {
  if (!toolPreview || typeof toolPreview !== 'object') return null

  const toolName = String(toolPreview.tool_name || '').toLowerCase()
  if (toolName !== 'search' && toolName !== 'read') return null

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
  if (!hasMetadata && !hasItems) return null

  return (
    <div
      style={{
        marginTop: 10,
        padding: '8px 10px',
        borderRadius: radii.md,
        background: colors.panelBg,
        border: `1px solid ${colors.accentBorderMid}`,
        fontSize: 14,
        color: colors.textSecondary,
      }}
    >
      <div style={{ fontWeight: 600, color: colors.accent }}>
        {toolName === 'search' ? 'Search preview' : 'Read preview'}
      </div>

      {code ? <div style={{ marginTop: 4 }}>Code: {truncatePreviewText(code, 80)}</div> : null}
      {reason ? <div style={{ marginTop: 4 }}>Reason: {truncatePreviewText(reason, 120)}</div> : null}
      {attemptedProviders.length > 0 ? (
        <div style={{ marginTop: 4 }}>Attempted: {truncatePreviewText(attemptedProviders.join(' → '), 120)}</div>
      ) : null}

      {hasItems ? (
        <div style={{ marginTop: 6 }}>
          {boundedItems.map((item, idx) => {
            const itemObject = item && typeof item === 'object' ? item : {}
            const titleCandidate = itemObject.title ?? itemObject.url ?? itemObject.source ?? itemObject.path ?? item
            const detailCandidate = itemObject.snippet ?? itemObject.text ?? itemObject.content ?? itemObject.reason
            return (
              <div key={`preview-item-${idx}`} style={{ marginTop: idx === 0 ? 0 : 4 }}>
                <div>{`${idx + 1}. ${truncatePreviewText(titleCandidate, 120)}`}</div>
                {detailCandidate != null ? (
                  <div style={{ opacity: 0.85, fontSize: 13 }}>{truncatePreviewText(detailCandidate, 120)}</div>
                ) : null}
              </div>
            )
          })}
          {overflowCount > 0 ? <div style={{ marginTop: 4, opacity: 0.85 }}>+{overflowCount} more</div> : null}
        </div>
      ) : null}
    </div>
  )
}

export function renderChatMessage(message, index) {
  const isUser = message.role === 'user'
  const isError = message.role === 'error'
  const rowJustify = isUser ? 'flex-end' : 'flex-start'
  const bubbleBg = isUser ? colors.userBubble : isError ? colors.errorBubble : colors.panelAltBg
  const bubbleBorder = isUser
    ? `1px solid ${colors.userBubble}`
    : isError
      ? `1px solid ${colors.danger}`
      : `1px solid ${colors.accentBorderStrong}`
  const bubbleShadow = isUser || isError ? 'none' : `0 0 10px ${colors.accentGlowMid}`

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
            borderRadius: radii.lg,
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
                    borderRadius: radii.md,
                    background: colors.panelBg,
                    border: '1px solid #ef444466',
                    fontSize: 14,
                    color: '#fca5a5',
                  }}
                >
                  <div>
                    {(Array.isArray(message.failure.attempted_providers) && message.failure.attempted_providers.length > 0
                      ? 'Search failed: '
                      : 'Tool failed: ') + String(message.failure.reason || 'unknown error')}
                  </div>
                  {Array.isArray(message.failure.attempted_providers) && message.failure.attempted_providers.length > 0 ? (
                    <div style={{ marginTop: 4 }}>Attempted: {message.failure.attempted_providers.join(' → ')}</div>
                  ) : null}
                  {message.failure.code ? <div style={{ marginTop: 4 }}>Code: {String(message.failure.code)}</div> : null}
                </div>
              ) : null}
              {renderToolPreview(message.tool_preview)}
              {message.attachment ? (
                <div
                  style={{
                    marginTop: 10,
                    padding: '8px 10px',
                    borderRadius: radii.md,
                    background: colors.panelBg,
                    border: `1px solid ${colors.accentBorderMid}`,
                    fontSize: 14,
                    color: colors.textSecondary,
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
}
