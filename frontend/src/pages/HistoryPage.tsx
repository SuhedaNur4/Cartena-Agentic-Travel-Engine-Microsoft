import { useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { useItineraryHistory } from '../hooks/useItineraryHistory'
import { Skeleton } from '../components/ui/Skeleton'
import { EmptyState } from '../components/ui/EmptyState'

const BUDGET_LABELS: Record<string, string> = {
  low: 'Budget', medium: 'Mid-range', high: 'Luxury', luxury: 'Ultra',
}

export function HistoryPage() {
  const { history, historyLoading } = useItineraryHistory()
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()
  const [showFavoritesOnly, setShowFavoritesOnly] = useState(false)

  const cityFilter = searchParams.get('city')

  const filteredHistory = history
    .filter(h => !showFavoritesOnly || h.is_favorite)
    .filter(h => !cityFilter || h.destination.toLowerCase() === cityFilter.toLowerCase())

  return (
    <div className="page-content">
      <div className="page-container">

        <div style={{ marginBottom: 'var(--space-10)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
            <div>
              <h1>Your Trips</h1>
              <p style={{ marginTop: 'var(--space-1)', fontSize: 'var(--text-sm)', color: 'var(--color-text-muted)' }}>
                {historyLoading
                  ? 'Loading history…'
                  : `${history.length} trip${history.length !== 1 ? 's' : ''} saved on this device`}
              </p>
            </div>
            <button
              onClick={() => setShowFavoritesOnly(!showFavoritesOnly)}
              style={{
                background: showFavoritesOnly ? '#FBB728' : 'var(--color-surface-2)',
                color: showFavoritesOnly ? '#12241d' : 'var(--color-text)',
                border: '1px solid var(--color-border)',
                padding: '6px 12px',
                borderRadius: 'var(--radius-pill)',
                fontFamily: 'inherit',
                fontWeight: 500,
                fontSize: 'var(--text-sm)',
                cursor: 'pointer',
                transition: 'all 0.2s',
                display: 'flex',
                alignItems: 'center',
                gap: '6px'
              }}
            >
              <span>{showFavoritesOnly ? '★' : '☆'}</span> Sadece Favoriler
            </button>
          </div>
          
          {cityFilter && (
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginTop: 'var(--space-3)' }}>
              <span style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-muted)' }}>Filtre:</span>
              <span style={{ display: 'inline-flex', alignItems: 'center', gap: '6px', background: 'var(--color-primary-subtle)', color: '#93c5fd', border: '1px solid rgba(59,130,246,0.3)', padding: '2px 10px', borderRadius: 'var(--radius-pill)', fontSize: 'var(--text-xs)', fontWeight: 500 }}>
                {cityFilter.charAt(0).toUpperCase() + cityFilter.slice(1)}
                <button onClick={() => setSearchParams({})} style={{ background: 'none', border: 'none', color: 'inherit', cursor: 'pointer', padding: 0, lineHeight: 1, fontSize: '14px', marginLeft: '2px' }}>&#215;</button>
              </span>
            </div>
          )}
        </div>

        {historyLoading && (
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))',
              gap: 'var(--space-4)',
            }}
          >
            {Array.from({ length: 6 }).map((_, i) => (
              <Skeleton key={i} height={120} borderRadius="var(--radius-md)" />
            ))}
          </div>
        )}

        {!historyLoading && filteredHistory.length === 0 && (
          <EmptyState
            title="No trips yet"
            description="You haven't generated any itineraries on this device. Start by planning your first trip."
            icon={
              <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                <path d="M4 19.5v-15A2.5 2.5 0 0 1 6.5 2H20v20H6.5a2.5 2.5 0 0 1 0-5H20"/>
              </svg>
            }
            action={
              <button className="btn btn-primary" onClick={() => navigate('/')}>
                Plan your first trip
              </button>
            }
          />
        )}

        {!historyLoading && filteredHistory.length > 0 && (
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))',
              gap: 'var(--space-4)',
            }}
          >
            {filteredHistory.map((item, i) => (
              <div
                key={item.id}
                className="card card--interactive"
                style={{
                  animation: `fadeIn 0.25s ease both`,
                  animationDelay: `${i * 40}ms`,
                }}
                onClick={() => navigate(`/itinerary/${item.id}`)}
                role="button"
                tabIndex={0}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' || e.key === ' ') navigate(`/itinerary/${item.id}`)
                }}
              >
                <div
                  style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'flex-start',
                    marginBottom: 'var(--space-2)',
                  }}
                >
                  <h3 style={{ color: 'var(--color-text)', fontWeight: 600, lineHeight: 1.3 }}>
                    {item.is_favorite && <span style={{ color: '#FBB728', marginRight: '6px' }}>★</span>}
                    {item.destination}
                  </h3>
                  <svg
                    width="14"
                    height="14"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="var(--color-text-muted)"
                    strokeWidth="1.75"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    style={{ flexShrink: 0, marginTop: 2 }}
                  >
                    <path d="M9 18l6-6-6-6" />
                  </svg>
                </div>

                <div
                  style={{
                    fontSize: 'var(--text-xs)',
                    color: 'var(--color-text-secondary)',
                    display: 'flex',
                    gap: 'var(--space-3)',
                    flexWrap: 'wrap',
                    marginBottom: 'var(--space-3)',
                  }}
                >
                  <span>{item.duration_days} {item.duration_days === 1 ? 'day' : 'days'}</span>
                  <span style={{ color: 'var(--color-border)' }}>·</span>
                  <span>{BUDGET_LABELS[item.budget]}</span>
                </div>

                <div style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-muted)' }}>
                  {new Date(item.created_at).toLocaleDateString(undefined, {
                    year: 'numeric',
                    month: 'short',
                    day: 'numeric',
                  })}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
