export const colors = {
  appBg: '#050810',
  panelBg: '#0a0e1a',
  panelAltBg: '#1a2332',
  textPrimary: '#e5f6ff',
  textMuted: '#8fb6c2',
  textSecondary: '#b8deeb',
  accent: '#00d4ff',
  accentBorderSoft: '#00d4ff33',
  accentBorderMid: '#00d4ff55',
  accentBorderStrong: '#00d4ff80',
  accentGlowSoft: '#00d4ff1f',
  accentGlowMid: '#00d4ff33',
  success: '#10b981',
  danger: '#ef4444',
  warning: '#f59e0b',
  userBubble: '#3b82f6',
  errorBubble: '#3a1111',
}

export const spacing = {
  headerPadding: '14px 18px',
  panelPadding: 16,
  composerPadding: 12,
  messageGap: 14,
  inputPadding: 10,
  buttonPadding: '8px 12px',
  sendButtonPadding: '10px 14px',
}

export const radii = {
  sm: 8,
  md: 10,
  lg: 20,
}

export const appStyles = {
  container: {
    height: '100vh',
    display: 'flex',
    flexDirection: 'column',
    fontFamily: 'Arial, sans-serif',
    background: colors.appBg,
    color: colors.textPrimary,
  },
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: spacing.headerPadding,
    borderBottom: `1px solid ${colors.accentBorderSoft}`,
    flexShrink: 0,
    background: colors.panelBg,
    boxShadow: `0 0 16px ${colors.accentGlowSoft}`,
  },
  headerLeft: { display: 'flex', alignItems: 'center', gap: 14 },
  title: { fontSize: 32, fontWeight: 700 },
  statusRow: { display: 'flex', alignItems: 'center', gap: 8, fontSize: 14, color: colors.textSecondary },
  divider: { opacity: 0.6 },
  headerButton: {
    border: `1px solid ${colors.accentBorderStrong}`,
    background: colors.panelAltBg,
    color: colors.accent,
    padding: spacing.buttonPadding,
    borderRadius: radii.md,
    cursor: 'pointer',
  },
  messagesContainer: {
    flex: 1,
    overflowY: 'auto',
    padding: spacing.panelPadding,
    background: colors.appBg,
  },
  emptyState: { color: colors.textMuted, fontSize: 18 },
  composer: {
    display: 'flex',
    gap: 8,
    padding: spacing.composerPadding,
    borderTop: `1px solid ${colors.accentBorderSoft}`,
    flexShrink: 0,
    background: colors.panelAltBg,
  },
  fileInput: { maxWidth: 220, color: colors.textPrimary },
  textInput: {
    flex: 1,
    padding: spacing.inputPadding,
    borderRadius: radii.md,
    border: `1px solid ${colors.accentBorderStrong}`,
    background: colors.panelBg,
    color: colors.textPrimary,
    outlineColor: colors.accent,
    fontSize: 18,
  },
  sendButton: {
    padding: spacing.sendButtonPadding,
    borderRadius: radii.md,
    border: `1px solid ${colors.accent}`,
    background: colors.accent,
    color: colors.appBg,
    fontWeight: 600,
  },
}

export function getSendButtonStyle(disabled) {
  return {
    ...appStyles.sendButton,
    cursor: disabled ? 'not-allowed' : 'pointer',
  }
}
