import { useSystemStore } from '../store/systemStore'

function StatusDot({ status }: { status: string | undefined }) {
  const color =
    status === 'healthy' ? 'var(--color-success)'
    : status === 'degraded' ? 'var(--color-warning)'
    : 'var(--color-error)'

  const label =
    status === 'healthy' ? 'Running'
    : status === 'degraded' ? 'Degraded'
    : 'Offline'

  return (
    <span style={{ display: 'inline-flex', alignItems: 'center', gap: 'var(--space-2)', fontSize: 'var(--text-xs)', fontWeight: 500, color }}>
      <span
        style={{
          width: 8,
          height: 8,
          borderRadius: '50%',
          background: color,
          display: 'inline-block',
          flexShrink: 0,
        }}
      />
      {label}
    </span>
  )
}

function SettingRow({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div
      style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        padding: 'var(--space-3) 0',
        borderBottom: '1px solid var(--color-border)',
        gap: 'var(--space-4)',
      }}
    >
      <span style={{ fontSize: 'var(--text-sm)', color: 'var(--color-text-secondary)', letterSpacing: '-0.01em' }}>
        {label}
      </span>
      <span style={{ fontSize: 'var(--text-sm)', color: 'var(--color-text)', textAlign: 'right' }}>
        {value}
      </span>
    </div>
  )
}

export function SettingsPage() {
  const health = useSystemStore((s) => s.health)
  const healthLoading = useSystemStore((s) => s.healthLoading)

  return (
    <div className="page-content">
      <div className="page-container">

        <div style={{ marginBottom: 'var(--space-10)' }}>
          <h1>Settings</h1>
          <p style={{ marginTop: 'var(--space-1)', fontSize: 'var(--text-sm)', color: 'var(--color-text-muted)' }}>
            AI engine configuration and status.
          </p>
        </div>

        <div style={{ maxWidth: 560, display: 'flex', flexDirection: 'column', gap: 'var(--space-8)' }}>

          <section>
            <h2 style={{ fontSize: 'var(--text-xs)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.07em', color: 'var(--color-text-muted)', marginBottom: 'var(--space-2)' }}>
              System Status
            </h2>
            <div
              style={{
                background: 'var(--color-surface)',
                border: '1px solid var(--color-border)',
                borderRadius: 'var(--radius-md)',
                padding: '0 var(--space-5)',
              }}
            >
              {healthLoading ? (
                <div style={{ padding: 'var(--space-6) 0', display: 'flex', alignItems: 'center', gap: 'var(--space-2)', color: 'var(--color-text-muted)', fontSize: 'var(--text-sm)' }}>
                  <div className="spinner" />
                  Checking status…
                </div>
              ) : health ? (
                <>
                  <SettingRow
                    label="AI Engine"
                    value={<StatusDot status={health.status} />}
                  />
                  <SettingRow
                    label="Knowledge Base"
                    value={health.kb_document_count != null ? `${health.kb_document_count.toLocaleString()} chunks` : 'Unavailable'}
                  />
                  <div style={{ padding: 'var(--space-3) 0' }}>
                    <details style={{ cursor: 'pointer' }}>
                      <summary style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-muted)', outline: 'none' }}>
                        Advanced details
                      </summary>
                      <div style={{ marginTop: 'var(--space-3)', padding: 'var(--space-3)', background: 'var(--color-surface-2)', borderRadius: 'var(--radius-sm)', border: '1px solid var(--color-border)' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 'var(--space-2)' }}>
                          <span style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-muted)' }}>Language Model</span>
                          <span style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-secondary)', fontFamily: 'monospace' }}>{health.llm_model || '—'}</span>
                        </div>
                        <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                          <span style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-muted)' }}>Embedding Model</span>
                          <span style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-secondary)', fontFamily: 'monospace' }}>{health.embedding_model || '—'}</span>
                        </div>
                      </div>
                    </details>
                  </div>
                </>
              ) : (
                <div style={{ padding: 'var(--space-6) 0', fontSize: 'var(--text-sm)', color: 'var(--color-text-muted)' }}>
                  Engine status unavailable. Make sure the backend is running.
                </div>
              )}
            </div>
          </section>

          <section>
            <h2 style={{ fontSize: 'var(--text-xs)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.07em', color: 'var(--color-text-muted)', marginBottom: 'var(--space-2)' }}>
              About
            </h2>
            <div
              style={{
                background: 'var(--color-surface)',
                border: '1px solid var(--color-border)',
                borderRadius: 'var(--radius-md)',
                padding: '0 var(--space-5)',
              }}
            >
              <SettingRow label="Application" value="Cartena Local" />
              <SettingRow label="Generation" value="On-device (Private)" />
              <SettingRow label="Storage" value="Local SQLite" />
            </div>
          </section>

        </div>
      </div>
    </div>
  )
}
