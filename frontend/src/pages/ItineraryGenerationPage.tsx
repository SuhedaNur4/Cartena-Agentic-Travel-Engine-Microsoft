import { useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useGenerateItinerary } from '../hooks/useGenerateItinerary'
import { Alert } from '../components/ui/Alert'

const STAGES = [
  'Understanding request',
  'Retrieving local knowledge',
  'Building AI prompt',
  'Generating itinerary',
  'Saving itinerary',
  'Completed'
]

export function ItineraryGenerationPage() {
  const navigate = useNavigate()
  const { isGenerating, currentStage, generatedId, error, cancel, streamedText } = useGenerateItinerary()

  useEffect(() => {
    if (!isGenerating && !generatedId && !error) {
      navigate('/', { replace: true })
    }
  }, []) 

  useEffect(() => {
    if (generatedId) {
      navigate(`/itinerary/${generatedId}`, { replace: true })
    }
  }, [generatedId, navigate])

  const currentIndex = STAGES.indexOf(currentStage)
  const wordCount = streamedText.split(/\s+/).filter(Boolean).length
  
  return (
    <div className="page-content">
      <div className="page-container">

        <div style={{ marginBottom: 'var(--space-10)' }}>
          <h1>Planning Your Trip</h1>
          <p style={{ marginTop: 'var(--space-1)', fontSize: 'var(--text-sm)', color: 'var(--color-text-muted)' }}>
            Cartena AI is building a highly tailored itinerary based on your preferences.
          </p>
        </div>

        <div
          style={{
            maxWidth: 680,
            display: 'flex',
            flexDirection: 'column',
            gap: 'var(--space-4)',
          }}
        >
          
          {error && (
            <Alert
              type="error"
              title="Generation Failed"
              message={error}
              action={
                <button
                  className="btn btn-ghost btn-sm"
                  onClick={() => navigate('/')}
                >
                  Back to planner
                </button>
              }
            />
          )}

          {isGenerating && (
            <div
              style={{
                background: 'var(--color-surface)',
                border: '1px solid var(--color-border)',
                borderRadius: 'var(--radius-md)',
                overflow: 'hidden',
                padding: 'var(--space-6) var(--space-8)',
                display: 'flex',
                flexDirection: 'column',
                gap: 'var(--space-6)'
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
                <button
                  type="button"
                  className="btn btn-ghost btn-sm"
                  onClick={() => { cancel(); navigate('/') }}
                >
                  Cancel
                </button>
              </div>

              <div aria-live="polite" style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-4)' }}>
                {STAGES.slice(0, -1).map((stage, idx) => {
                  const isCompleted = currentIndex > idx || currentStage === 'Completed'
                  const isActive = currentIndex === idx

                  return (
                    <div key={stage} style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-4)' }}>
                      
                      <div style={{ width: 24, height: 24, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                        {isCompleted ? (
                          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="var(--color-success)" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                            <polyline points="20 6 9 17 4 12"></polyline>
                          </svg>
                        ) : isActive ? (
                          <div className="spinner" style={{ width: 18, height: 18 }} />
                        ) : (
                          <div style={{ width: 12, height: 12, borderRadius: '50%', background: 'var(--color-border)', opacity: 0.5 }} />
                        )}
                      </div>

                      <span style={{ 
                        fontSize: 'var(--text-sm)', 
                        fontWeight: isActive ? 500 : 400,
                        color: isCompleted ? 'var(--color-text)' : isActive ? 'var(--color-primary)' : 'var(--color-text-muted)'
                      }}>
                        {stage}
                        {stage === 'Generating itinerary' && isActive && wordCount > 0 && (
                          <span style={{ marginLeft: 'var(--space-2)', fontSize: 'var(--text-xs)', color: 'var(--color-text-muted)' }}>
                            ({wordCount} words generated...)
                          </span>
                        )}
                      </span>
                    </div>
                  )
                })}
              </div>
            </div>
          )}
        </div>

      </div>
    </div>
  )
}
