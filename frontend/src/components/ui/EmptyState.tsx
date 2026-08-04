import React from 'react'

interface EmptyStateProps {
  title: string
  description?: string
  icon?: React.ReactNode
  action?: React.ReactNode
}

export function EmptyState({ title, description, icon, action }: EmptyStateProps) {
  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        padding: 'var(--space-16) var(--space-6)',
        background: 'var(--color-surface)',
        border: '1px solid var(--color-border)',
        borderRadius: 'var(--radius-md)',
        textAlign: 'center',
      }}
    >
      {icon && (
        <div style={{ color: 'var(--color-text-muted)', marginBottom: 'var(--space-4)' }}>
          {icon}
        </div>
      )}
      <h3 style={{ fontSize: 'var(--text-base)', color: 'var(--color-text)', marginBottom: 'var(--space-1)' }}>
        {title}
      </h3>
      {description && (
        <p style={{ fontSize: 'var(--text-sm)', color: 'var(--color-text-secondary)', marginBottom: 'var(--space-6)', maxWidth: 400 }}>
          {description}
        </p>
      )}
      {action && <div>{action}</div>}
    </div>
  )
}
