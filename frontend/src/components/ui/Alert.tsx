import React from 'react'

interface AlertProps {
  type?: 'info' | 'success' | 'warning' | 'error'
  title?: string
  message: React.ReactNode
  action?: React.ReactNode
}

export function Alert({ type = 'info', title, message, action }: AlertProps) {
  const isError = type === 'error'
  const isWarning = type === 'warning'
  const isSuccess = type === 'success'

  const bg = isError ? 'var(--color-error-bg)' : isWarning ? 'var(--color-warning-bg)' : isSuccess ? 'var(--color-success-bg)' : 'var(--color-surface-2)'
  const border = isError ? 'var(--color-error)' : isWarning ? 'var(--color-warning)' : isSuccess ? 'var(--color-success)' : 'var(--color-border)'
  const color = isError ? 'var(--color-error)' : isWarning ? 'var(--color-warning)' : isSuccess ? 'var(--color-success)' : 'var(--color-text)'

  return (
    <div
      role={isError ? 'alert' : 'status'}
      style={{
        padding: 'var(--space-3) var(--space-4)',
        borderRadius: 'var(--radius-md)',
        background: bg,
        border: `1px solid ${border}`,
        opacity: 0.8,
        display: 'flex',
        alignItems: action ? 'center' : 'flex-start',
        justifyContent: 'space-between',
        gap: 'var(--space-4)',
      }}
    >
      <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-1)' }}>
        {title && (
          <span style={{ fontSize: 'var(--text-sm)', fontWeight: 600, color }}>
            {title}
          </span>
        )}
        <span style={{ fontSize: 'var(--text-sm)', color: title ? 'var(--color-text)' : color }}>
          {message}
        </span>
      </div>
      {action && <div>{action}</div>}
    </div>
  )
}
