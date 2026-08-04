import { useEffect } from 'react'
import { useParams, Link, useNavigate } from 'react-router-dom'
import { useItinerary } from '../hooks/useItinerary'
import { useItineraryStore } from '../store/itineraryStore'
import { ItineraryView } from '../components/itinerary/ItineraryView'
import { Skeleton } from '../components/ui/Skeleton'
import { Alert } from '../components/ui/Alert'
import ReactMarkdown from 'react-markdown'

export function ItineraryPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()

  const { itinerary, loading, error } = useItinerary(id === 'new' ? undefined : id)

  const isGenerating = useItineraryStore((s) => s.isGenerating)
  const streamedText = useItineraryStore((s) => s.streamedText)
  const currentStage = useItineraryStore((s) => s.currentStage)
  const generatedId = useItineraryStore((s) => s.generatedId)
  const generateError = useItineraryStore((s) => s.error)
  const storeKbMiss = useItineraryStore((s) => s.kbMiss)
  const qualityWarnings = useItineraryStore((s) => s.qualityWarnings)

  useEffect(() => {
    if (id === 'new' && generatedId && !isGenerating) {
      navigate(`/itinerary/${generatedId}`, { replace: true })
    }
  }, [id, generatedId, isGenerating, navigate])

  const kbMiss = id === 'new' ? storeKbMiss : (itinerary?.kb_miss ?? false)
  const isLoading = id === 'new' ? isGenerating : loading
  const pageError = id === 'new' ? generateError : error

  return (
    <div style={{ flex: 1, display: 'flex', flexDirection: 'column', background: 'var(--color-bg)' }}>
      
      <div style={{ position: 'relative', minHeight: '400px', overflow: 'hidden', background: 'radial-gradient(120% 90% at 25% 15%,#2a4a3c 0%,#163026 45%,#0d1f18 100%)', display: 'flex', alignItems: 'center' }}>
        <div style={{ position: 'absolute', inset: 0, background: 'linear-gradient(180deg,rgba(13,31,24,.1),rgba(13,31,24,.55)),radial-gradient(80% 60% at 20% 80%,rgba(240,107,4,.22),transparent 60%),conic-gradient(from 210deg at 78% 30%,rgba(44,159,199,.35),transparent 40%)' }}></div>
        <div style={{ position: 'absolute', left: 0, right: 0, bottom: 0, height: '230px', background: 'linear-gradient(180deg,transparent,rgba(9,20,15,.85)),repeating-linear-gradient(120deg,rgba(255,255,255,.03) 0 2px,transparent 2px 8px)', clipPath: 'polygon(0 60%,12% 30%,24% 55%,38% 18%,52% 48%,66% 22%,80% 50%,100% 28%,100% 100%,0 100%)' }}></div>
        
        <div style={{ position: 'relative', padding: '70px 48px', maxWidth: '620px', width: '100%', zIndex: 10 }}>
          <div style={{ display: 'inline-flex', alignItems: 'center', marginBottom: '26px' }}>
            <img src="/cartenalogo.png" alt="Cartena Logo" style={{ width: '48px', height: '48px', borderRadius: '50%', objectFit: 'cover' }} />
          </div>
          <h1 style={{ fontFamily: '"Yeseva One", serif', fontWeight: 400, fontSize: '64px', lineHeight: 0.98, color: '#F5ECD2', margin: '0 0 20px', letterSpacing: '-0.01em' }}>
            {id === 'new' ? 'Building Your Trip' : (itinerary?.destination || 'Loading...')}
          </h1>
          <p style={{ fontFamily: '"DM Sans", sans-serif', fontWeight: 400, fontSize: '17px', lineHeight: 1.6, color: 'rgba(245,236,210,.82)', maxWidth: '440px', margin: '0 0 30px', textWrap: 'pretty' }}>
            {id === 'new'
              ? 'Please wait — Cartena AI is building a personalised itinerary using local knowledge.'
              : 'Your day-by-day itinerary, tailored to your destination and preferences.'}
          </p>
          <div style={{ display: 'flex', gap: '14px', alignItems: 'center' }}>
            <Link to="/" style={{ background: 'transparent', color: '#F5ECD2', border: '1px solid rgba(245,236,210,.28)', padding: '15px 24px', borderRadius: '9999px', fontWeight: 600, fontSize: '15px', fontFamily: '"DM Sans", sans-serif', cursor: 'pointer', textDecoration: 'none' }}>
              Back to Planner
            </Link>
          </div>
        </div>
      </div>

      <div style={{ padding: '56px 48px', background: 'var(--color-bg)', flex: 1, display: 'flex', justifyContent: 'center' }}>
        <div style={{ width: '100%', maxWidth: '1000px' }}>
          
          <div style={{ marginBottom: 'var(--space-8)' }}>
            <Link
              to="/history"
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: 'var(--space-2)',
                fontSize: 'var(--text-sm)',
                color: 'var(--color-text-muted)',
                textDecoration: 'none',
                letterSpacing: '-0.01em',
                transition: 'color var(--transition-fast)',
              }}
              onMouseEnter={(e) => (e.currentTarget.style.color = 'var(--color-text-secondary)')}
              onMouseLeave={(e) => (e.currentTarget.style.color = 'var(--color-text-muted)')}
            >
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M15 18l-6-6 6-6" />
              </svg>
              All itineraries
            </Link>
          </div>

          {pageError && !isLoading && (
            <div style={{ maxWidth: 480 }}>
              <Alert
                type="error"
                title="Something went wrong"
                message={pageError}
              />
            </div>
          )}

          {id === 'new' && isGenerating && (
            <div style={{ background: 'var(--color-surface)', padding: '32px', borderRadius: 'var(--radius-lg)', color: 'var(--color-text)', border: '1px solid var(--color-border)', boxShadow: '0 20px 40px -10px rgba(0,0,0,0.5)' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '24px', paddingBottom: '16px', borderBottom: '1px dashed var(--color-border)' }}>
                <span className="spinner" style={{ borderColor: 'var(--color-primary)', borderRightColor: 'transparent', width: '20px', height: '20px' }} />
                <span style={{ fontFamily: '"DM Sans", sans-serif', fontWeight: 600, color: 'var(--color-primary)' }}>{currentStage || 'Generating plan...'}</span>
              </div>
              <div style={{ fontFamily: '"DM Sans", sans-serif', lineHeight: 1.6, opacity: 0.8, whiteSpace: 'pre-wrap' }}>
                <ReactMarkdown>{streamedText || '...'}</ReactMarkdown>
              </div>
            </div>
          )}

          {id !== 'new' && isLoading && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-4)' }}>
              <Skeleton height={140} borderRadius="var(--radius-md)" />
              <Skeleton height={200} borderRadius="var(--radius-md)" />
              <Skeleton height={200} borderRadius="var(--radius-md)" />
            </div>
          )}

          {id !== 'new' && itinerary && !isLoading && (
            <>
              {qualityWarnings && qualityWarnings.length > 0 && (
                <div style={{ marginBottom: '40px', padding: '24px', background: 'rgba(240, 107, 4, 0.05)', border: '1px solid rgba(240, 107, 4, 0.2)', borderRadius: 'var(--radius-lg)' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '16px', color: '#F06B04', fontWeight: 600, fontFamily: '"DM Sans", sans-serif' }}>
                    <span style={{ fontSize: '20px' }}>🛡️</span>
                    System Audit (AI Warnings)
                  </div>
                  <ul style={{ margin: 0, paddingLeft: '24px', color: 'var(--color-text-secondary)', fontFamily: '"DM Sans", sans-serif', fontSize: '15px', lineHeight: 1.6 }}>
                    {qualityWarnings.map((warning, idx) => (
                      <li key={idx} style={{ marginBottom: '8px' }}>{warning}</li>
                    ))}
                  </ul>
                </div>
              )}
              
              <h2 style={{ fontFamily: '"Yeseva One", serif', fontWeight: 400, fontSize: '40px', margin: '0 0 40px', color: 'var(--color-text)' }}>
                Day-by-Day Itinerary
              </h2>
              <ItineraryView
                itinerary={itinerary}
                kbMiss={kbMiss}
              />
            </>
          )}

        </div>
      </div>
    </div>
  )
}

