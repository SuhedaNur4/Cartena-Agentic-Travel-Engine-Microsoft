import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'

interface DestinationSummary {
  destination: string
  trips: number
  last_planned: string
}

export function DestinationsPage() {
  const [destinations, setDestinations] = useState<DestinationSummary[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetch('/api/v1/destinations/')
      .then((r) => r.json())
      .then((data) => {
        setDestinations(data)
        setLoading(false)
      })
      .catch((err) => {
        console.error('Error fetching destinations:', err)
        setLoading(false)
      })
  }, [])

  return (
    <div className="page-content" style={{ background: 'linear-gradient(180deg,#12241d,#0d1f18)', minHeight: '100vh' }}>
      <div style={{ padding: '60px 48px', maxWidth: '1000px', margin: '0 auto', width: '100%' }}>
        <div style={{ marginBottom: '48px' }}>
          <div style={{ fontFamily: '"DM Sans", sans-serif', fontWeight: 600, fontSize: '12px', letterSpacing: '0.18em', textTransform: 'uppercase', color: '#2C9FC7', marginBottom: '12px' }}>Your world</div>
          <h1 style={{ fontFamily: '"Yeseva One", serif', fontWeight: 400, fontSize: '42px', color: '#F5ECD2', margin: '0 0 12px' }}>
            Destinations
          </h1>
          <p style={{ fontFamily: '"DM Sans", sans-serif', fontSize: '15px', color: 'rgba(245,236,210,.6)', margin: 0, maxWidth: '560px', lineHeight: 1.6 }}>
            All cities you've planned a trip to. Click any destination to see its itineraries.
          </p>
        </div>

        {loading ? (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: '24px' }}>
            {Array.from({ length: 4 }).map((_, i) => (
              <div key={i} style={{ height: '140px', borderRadius: '16px', background: 'rgba(245,236,210,.05)', border: '1px solid rgba(245,236,210,.1)', animation: 'pulse 1.5s ease-in-out infinite' }} />
            ))}
          </div>
        ) : destinations.length === 0 ? (
          <div style={{ fontFamily: '"DM Sans", sans-serif', color: 'rgba(245,236,210,.5)', padding: '60px 40px', background: 'rgba(245,236,210,.04)', borderRadius: '16px', textAlign: 'center', border: '1px solid rgba(245,236,210,.1)' }}>
            <div style={{ fontSize: '32px', marginBottom: '16px' }}>🗺️</div>
            <div style={{ fontSize: '16px', fontWeight: 600, color: 'rgba(245,236,210,.8)', marginBottom: '8px' }}>No destinations yet</div>
            <div style={{ fontSize: '14px' }}>Create your first itinerary and your destinations will appear here.</div>
          </div>
        ) : (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: '24px' }}>
            {destinations.map((dest) => (
              <Link 
                key={dest.destination}
                to={`/history?city=${encodeURIComponent(dest.destination)}`} 
                style={{ textDecoration: 'none' }}
              >
                <div 
                  style={{ 
                    background: 'rgba(245,236,210,.06)',
                    borderRadius: '16px', 
                    padding: '28px 24px', 
                    border: '1px solid rgba(245,236,210,.12)',
                    transition: 'all 0.2s',
                    cursor: 'pointer'
                  }}
                  onMouseOver={(e) => {
                    e.currentTarget.style.background = 'rgba(245,236,210,.1)'
                    e.currentTarget.style.borderColor = 'rgba(245,236,210,.2)'
                    e.currentTarget.style.transform = 'translateY(-3px)'
                  }}
                  onMouseOut={(e) => {
                    e.currentTarget.style.background = 'rgba(245,236,210,.06)'
                    e.currentTarget.style.borderColor = 'rgba(245,236,210,.12)'
                    e.currentTarget.style.transform = 'translateY(0)'
                  }}
                >
                  
                  <div style={{ width: '44px', height: '44px', borderRadius: '12px', background: 'linear-gradient(135deg,#F06B04,#FBB728)', display: 'flex', alignItems: 'center', justifyContent: 'center', marginBottom: '16px', fontSize: '20px' }}>🏙️</div>

                  <div style={{ fontFamily: '"Yeseva One", serif', fontSize: '22px', color: '#F5ECD2', marginBottom: '12px' }}>
                    {dest.destination.charAt(0).toUpperCase() + dest.destination.slice(1)}
                  </div>
                  
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontFamily: '"DM Sans", sans-serif', fontSize: '13px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: '#FBB728', fontWeight: 600 }}>
                      <span>{dest.trips}</span>
                      <span style={{ color: 'rgba(245,236,210,.5)', fontWeight: 400 }}>plans</span>
                    </div>
                    <div style={{ color: 'rgba(245,236,210,.45)', fontSize: '12px' }}>
                      Last: {new Date(dest.last_planned).toLocaleDateString()}
                    </div>
                  </div>
                </div>
              </Link>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
