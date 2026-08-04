import { useEffect, useState } from 'react'
import { useNavigate, useSearchParams, Link } from 'react-router-dom'
import { useSystemStore } from '../store/systemStore'
import { useGenerateItinerary } from '../hooks/useGenerateItinerary'
import { TripForm } from '../components/itinerary/TripForm'
import { getItineraries } from '../services/api'
import type { TripRequest, ItinerarySummary } from '../types/itinerary'



export function PlannerPage() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const initialDestination = searchParams.get('destination') || ''

  const health = useSystemStore((s) => s.health)
  const healthLoading = useSystemStore((s) => s.healthLoading)
  const { generate } = useGenerateItinerary()
  const [showForm, setShowForm] = useState(!!initialDestination)

  const [recentItineraries, setRecentItineraries] = useState<ItinerarySummary[]>([])
  const [recentLoading, setRecentLoading] = useState(true)

  const engineOffline = !healthLoading && health !== null && health.status === 'offline'

  useEffect(() => {
    getItineraries(6)
      .then(setRecentItineraries)
      .catch(() => setRecentItineraries([]))
      .finally(() => setRecentLoading(false))
  }, [])

  const handleGenerate = (request: TripRequest) => {
    generate(request)
    navigate('/itinerary/new')
  }

  return (
    <div style={{ flex: 1, display: 'flex', flexDirection: 'column', background: 'var(--color-bg)' }}>
      
      <div style={{ position: 'relative', minHeight: '520px', overflow: 'hidden', background: 'radial-gradient(120% 90% at 25% 15%,#2a4a3c 0%,#163026 45%,#0d1f18 100%)', display: 'flex', alignItems: 'center' }}>
        
        <div style={{ position: 'absolute', inset: 0, background: 'linear-gradient(180deg,rgba(13,31,24,.1),rgba(13,31,24,.55)),radial-gradient(80% 60% at 20% 80%,rgba(240,107,4,.22),transparent 60%),conic-gradient(from 210deg at 78% 30%,rgba(44,159,199,.35),transparent 40%)' }} />
        <div style={{ position: 'absolute', left: 0, right: 0, bottom: 0, height: '200px', background: 'linear-gradient(180deg,transparent,rgba(9,20,15,.85))', clipPath: 'polygon(0 60%,12% 30%,24% 55%,38% 18%,52% 48%,66% 22%,80% 50%,100% 28%,100% 100%,0 100%)' }} />

        <div style={{ position: 'relative', padding: '70px 48px', maxWidth: '640px', width: '100%', zIndex: 10 }}>

          <h1 style={{ fontFamily: '"Yeseva One", serif', fontWeight: 400, fontSize: '62px', lineHeight: 0.98, color: '#F5ECD2', margin: '0 0 20px', letterSpacing: '-0.01em' }}>
            Plan your trip,<br /><span style={{ fontStyle: 'italic', color: '#FBB728' }}>your way.</span>
          </h1>

          <p style={{ fontFamily: '"DM Sans", sans-serif', fontWeight: 400, fontSize: '17px', lineHeight: 1.6, color: 'rgba(245,236,210,.82)', maxWidth: '460px', margin: '0 0 32px' }}>
            Enter your destination, duration, and preferences. Cartena builds a day-by-day itinerary using local AI — no cloud, no account.
          </p>

          <div style={{ display: 'flex', gap: '14px', alignItems: 'center' }}>
            <button
              onClick={() => setShowForm(true)}
              style={{ display: 'inline-flex', alignItems: 'center', gap: '9px', background: '#F06B04', color: '#fff', border: 'none', padding: '15px 28px', borderRadius: '9999px', fontWeight: 600, fontSize: '15px', fontFamily: '"DM Sans", sans-serif', cursor: 'pointer', boxShadow: '0 12px 28px -10px rgba(240,107,4,.7)' }}
            >
              Create itinerary <span style={{ fontSize: '17px' }}>↗</span>
            </button>
            <Link
              to="/history"
              style={{ background: 'transparent', color: '#F5ECD2', border: '1px solid rgba(245,236,210,.28)', padding: '15px 24px', borderRadius: '9999px', fontWeight: 600, fontSize: '15px', fontFamily: '"DM Sans", sans-serif', cursor: 'pointer', textDecoration: 'none' }}
            >
              Explore plans
            </Link>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginTop: '34px', fontWeight: 500, fontSize: '12px', fontFamily: '"DM Sans", sans-serif', color: 'rgba(245,236,210,.55)' }}>
          </div>
        </div>
      </div>

      {showForm && (
        <div style={{ position: 'fixed', inset: 0, zIndex: 100, display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'rgba(0,0,0,.7)', backdropFilter: 'blur(4px)' }}>
          <div style={{ width: '100%', maxWidth: '600px', maxHeight: '90vh', overflowY: 'auto', background: '#F5ECD2', borderRadius: '24px', padding: '32px', boxShadow: '0 24px 48px -12px rgba(0,0,0,0.5)', border: '1px solid rgba(0,0,0,.08)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
              <h2 style={{ fontFamily: '"Yeseva One", serif', fontSize: '28px', margin: 0, color: '#241a10' }}>New trip</h2>
              <button onClick={() => setShowForm(false)} style={{ background: 'transparent', border: 'none', cursor: 'pointer', fontSize: '28px', color: '#241a10', opacity: 0.5, lineHeight: 1 }}>×</button>
            </div>
            <TripForm
              onGenerate={handleGenerate}
              isGenerating={false}
              onCancel={() => setShowForm(false)}
              engineOffline={engineOffline}
              initialDestination={initialDestination}
            />
          </div>
        </div>
      )}

      <div style={{ padding: '56px 48px 64px', background: '#F5ECD2' }}>
        <div style={{ display: 'flex', alignItems: 'flex-end', justifyContent: 'space-between', marginBottom: '32px' }}>
          <div>
            <div style={{ fontFamily: '"DM Sans", sans-serif', fontWeight: 600, fontSize: '12px', letterSpacing: '.18em', textTransform: 'uppercase', color: '#F06B04' }}>
              Your plans
            </div>
            <h2 style={{ fontFamily: '"Yeseva One", serif', fontWeight: 400, fontSize: '38px', margin: '6px 0 0', color: '#241a10' }}>
              Recent Itineraries
            </h2>
          </div>
          <Link
            to="/history"
            style={{ fontFamily: '"DM Sans", sans-serif', fontWeight: 600, fontSize: '14px', color: '#F06B04', textDecoration: 'none', display: 'inline-flex', alignItems: 'center', gap: '6px' }}
          >
            View all <span>→</span>
          </Link>
        </div>

        {recentLoading && (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '22px' }}>
            {[1, 2, 3].map((i) => (
              <div key={i} style={{ borderRadius: '16px', overflow: 'hidden', background: '#fff', border: '1px solid rgba(36,26,16,.1)', height: '200px', opacity: 0.4 }} />
            ))}
          </div>
        )}

        {!recentLoading && recentItineraries.length === 0 && (
          <div style={{ textAlign: 'center', padding: '60px 0' }}>
            <div style={{ fontSize: '40px', marginBottom: '16px' }}>🗺</div>
            <div style={{ fontFamily: '"Yeseva One", serif', fontSize: '24px', color: '#241a10', marginBottom: '10px' }}>No trips yet</div>
            <p style={{ fontFamily: '"DM Sans", sans-serif', fontSize: '15px', color: '#8c7e6c', maxWidth: '340px', margin: '0 auto 24px' }}>
              Create your first itinerary and it will appear here.
            </p>
            <button
              onClick={() => setShowForm(true)}
              style={{ background: '#F06B04', color: '#fff', border: 'none', padding: '13px 26px', borderRadius: '9999px', fontWeight: 600, fontSize: '14px', fontFamily: '"DM Sans", sans-serif', cursor: 'pointer' }}
            >
              Create itinerary
            </button>
          </div>
        )}

        {!recentLoading && recentItineraries.length > 0 && (
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-start', position: 'relative', marginTop: '20px' }}>
            <div style={{ position: 'absolute', left: '24px', top: '24px', bottom: '60px', width: '2px', borderLeft: '2px dashed rgba(36,26,16,.15)' }} />

            <div style={{ display: 'flex', gap: '20px', alignItems: 'center', position: 'relative', zIndex: 1, marginBottom: '24px', width: '100%' }}>
              <div style={{ width: '48px', height: '48px', borderRadius: '50%', background: '#F06B04', flex: 'none', display: 'flex', alignItems: 'center', justifyContent: 'center', boxShadow: '0 0 0 4px #F5ECD2', color: '#fff', fontSize: '24px' }}>
                🗺
              </div>
              <Link
                to={`/itinerary/${recentItineraries[0].id}`}
                style={{ textDecoration: 'none', background: '#fff', padding: '24px', borderRadius: '16px', border: '1px solid rgba(36,26,16,.1)', boxShadow: '0 8px 24px -12px rgba(36,26,16,.15)', flex: 1, maxWidth: '600px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', transition: 'transform 0.15s ease' }}
                onMouseEnter={(e) => { e.currentTarget.style.transform = 'translateY(-2px)' }}
                onMouseLeave={(e) => { e.currentTarget.style.transform = 'none' }}
              >
                <div>
                  <div style={{ fontFamily: '"DM Sans", sans-serif', fontWeight: 600, fontSize: '12px', color: '#F06B04', textTransform: 'uppercase', letterSpacing: '.1em', marginBottom: '6px' }}>Recently Planned</div>
                  <div style={{ fontFamily: '"Yeseva One", serif', fontSize: '28px', color: '#241a10', marginBottom: '8px' }}>{recentItineraries[0].destination}</div>
                  <div style={{ fontFamily: '"DM Sans", sans-serif', fontSize: '14px', color: '#8c7e6c' }}>
                    {recentItineraries[0].duration_days} days • {recentItineraries[0].budget}
                  </div>
                </div>
                <div style={{ fontSize: '24px', color: 'rgba(36,26,16,.2)' }}>→</div>
              </Link>
            </div>

            {recentItineraries.slice(1, 4).map((itin) => (
              <div key={itin.id} style={{ display: 'flex', gap: '20px', alignItems: 'center', position: 'relative', zIndex: 1, marginBottom: '16px', width: '100%' }}>
                <div style={{ width: '24px', height: '24px', borderRadius: '50%', background: '#fff', border: '2px solid rgba(36,26,16,.2)', flex: 'none', marginLeft: '12px' }} />
                <Link
                  to={`/itinerary/${itin.id}`}
                  style={{ textDecoration: 'none', background: 'transparent', padding: '12px 16px', borderRadius: '12px', border: '1px solid rgba(36,26,16,.08)', display: 'flex', justifyContent: 'space-between', alignItems: 'center', maxWidth: '400px', flex: 1, transition: 'background 0.15s ease' }}
                  onMouseEnter={(e) => { e.currentTarget.style.background = 'rgba(255,255,255,0.5)' }}
                  onMouseLeave={(e) => { e.currentTarget.style.background = 'transparent' }}
                >
                  <div>
                    <div style={{ fontFamily: '"DM Sans", sans-serif', fontWeight: 600, fontSize: '16px', color: '#241a10' }}>{itin.destination}</div>
                    <div style={{ fontFamily: '"DM Sans", sans-serif', fontSize: '13px', color: '#8c7e6c' }}>{itin.duration_days} days</div>
                  </div>
                </Link>
              </div>
            ))}

            <Link
              to="/history"
              style={{ display: 'inline-flex', alignItems: 'center', gap: '8px', fontFamily: '"DM Sans", sans-serif', fontWeight: 600, fontSize: '14px', color: '#F06B04', textDecoration: 'none', marginLeft: '68px', marginTop: '12px' }}
            >
              Devamı →
            </Link>
          </div>
        )}
      </div>

      <div style={{ padding: '56px 48px 72px', background: '#fff', borderTop: '1px solid rgba(36,26,16,.08)' }}>
        <div style={{ maxWidth: '800px', margin: '0 auto', textAlign: 'center' }}>
          <div style={{ fontFamily: '"DM Sans", sans-serif', fontWeight: 600, fontSize: '12px', letterSpacing: '.18em', textTransform: 'uppercase', color: '#F06B04', marginBottom: '12px' }}>
            How it works
          </div>
          <h2 style={{ fontFamily: '"Yeseva One", serif', fontWeight: 400, fontSize: '38px', color: '#241a10', margin: '0 0 48px' }}>
            AI planning, validated on every step
          </h2>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '32px' }}>
            {[
              { step: '01', title: 'You describe the trip', desc: 'Destination, duration, budget, interests, and any special requirements.' },
              { step: '02', title: 'Local knowledge retrieved', desc: 'Cartena searches a curated local knowledge base relevant to your destination.' },
              { step: '03', title: 'AI builds the plan', desc: 'Qwen3-4B generates a structured day-by-day itinerary on your device.' },
              { step: '04', title: 'Validated & saved', desc: 'A deterministic engine checks constraints and repairs issues before saving.' },
            ].map((s) => (
              <div key={s.step} style={{ textAlign: 'left' }}>
                <div style={{ fontFamily: '"DM Sans", sans-serif', fontWeight: 700, fontSize: '28px', color: '#F06B04', marginBottom: '12px', lineHeight: 1 }}>{s.step}</div>
                <div style={{ fontFamily: '"Yeseva One", serif', fontSize: '17px', color: '#241a10', marginBottom: '8px' }}>{s.title}</div>
                <p style={{ fontFamily: '"DM Sans", sans-serif', fontSize: '13px', color: '#8c7e6c', lineHeight: 1.6, margin: 0 }}>{s.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
