import { useState } from 'react'
import type { Itinerary } from '../../types/itinerary'
import { DayCard } from './DayCard'
import { MapWidget } from './MapWidget'

interface ItineraryViewProps {
  itinerary: Itinerary
  kbMiss?: boolean
  kbChunks?: number
}

export function ItineraryView({ itinerary }: ItineraryViewProps) {
  const [mapEnabled, setMapEnabled] = useState(false)
  const [isFavorite, setIsFavorite] = useState(itinerary.is_favorite)
  const [isToggling, setIsToggling] = useState(false)

  const handleToggleFavorite = async () => {
    setIsToggling(true)
    try {
      const res = await fetch(`/api/v1/itineraries/${itinerary.id}/favorite`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ is_favorite: !isFavorite })
      })
      if (res.ok) {
        setIsFavorite(!isFavorite)
      }
    } catch (err) {
      console.error(err)
    } finally {
      setIsToggling(false)
    }
  }

  const handlePrint = () => {
    window.print()
  }

  const markers = itinerary.days.flatMap(day => {
    const dayMarkers = []
    if (day.morning.lat && day.morning.lon) dayMarkers.push({ label: day.morning.location || 'Morning', lat: day.morning.lat, lon: day.morning.lon })
    if (day.afternoon.lat && day.afternoon.lon) dayMarkers.push({ label: day.afternoon.location || 'Afternoon', lat: day.afternoon.lat, lon: day.afternoon.lon })
    if (day.evening.lat && day.evening.lon) dayMarkers.push({ label: day.evening.location || 'Evening', lat: day.evening.lat, lon: day.evening.lon })
    return dayMarkers
  })

  return (
    <div style={{ padding: '60px 48px 66px', background: 'linear-gradient(180deg,#12241d,#0d1f18)', color: '#F5ECD2', position: 'relative', width: '100%' }}>
      
      <div className="no-print" style={{ position: 'absolute', top: '40px', right: '48px', display: 'flex', gap: '12px' }}>
        <button 
          onClick={handleToggleFavorite}
          disabled={isToggling}
          style={{ 
            background: isFavorite ? '#FBB728' : 'rgba(245,236,210,.1)', 
            color: isFavorite ? '#12241d' : '#F5ECD2', 
            border: 'none', 
            padding: '8px 16px', 
            borderRadius: '20px', 
            fontFamily: '"DM Sans", sans-serif', 
            fontWeight: 600, 
            fontSize: '14px', 
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            transition: 'all 0.2s'
          }}>
          <span style={{ fontSize: '16px' }}>{isFavorite ? '★' : '☆'}</span> {isFavorite ? 'In favorites' : 'Add to favorites'}
        </button>
        <button 
          onClick={handlePrint}
          style={{ 
            background: 'rgba(245,236,210,.1)', 
            color: '#F5ECD2', 
            border: 'none', 
            padding: '8px 16px', 
            borderRadius: '20px', 
            fontFamily: '"DM Sans", sans-serif', 
            fontWeight: 600, 
            fontSize: '14px', 
            cursor: 'pointer',
            transition: 'all 0.2s'
          }}>
          🖨 Print
        </button>
      </div>

      <div style={{ textAlign: 'center', marginBottom: '12px' }}>
        <div style={{ fontFamily: '"DM Sans", sans-serif', fontWeight: 600, fontSize: '12px', letterSpacing: '0.18em', textTransform: 'uppercase', color: '#2C9FC7' }}>Day by day</div>
        <h2 style={{ fontFamily: '"Yeseva One", serif', fontWeight: 400, fontSize: '42px', margin: '8px 0 0', color: '#F5ECD2' }}>Your Itinerary</h2>
        <p style={{ fontFamily: '"DM Sans", sans-serif', fontWeight: 400, fontSize: '15px', lineHeight: 1.5, color: 'rgba(245,236,210,.6)', maxWidth: '440px', margin: '12px auto 0' }}>
          Tap any day to see details. You can regenerate a day if you want a different plan.
        </p>
      </div>

      <div style={{ position: 'relative', maxWidth: '900px', margin: '44px auto 0' }}>
        <div style={{ position: 'absolute', left: '50%', top: 0, bottom: 0, width: '2px', background: 'repeating-linear-gradient(180deg,rgba(245,236,210,.35) 0 8px,transparent 8px 16px)', transform: 'translateX(-50%)' }}></div>
        {itinerary.days.map((day, i) => (
          <DayCard key={day.day_number} day={day} index={i} destination={itinerary.destination} itineraryId={itinerary.id} />
        ))}
      </div>

      <div className="no-print" style={{ display: 'grid', gridTemplateColumns: '1.3fr 1fr', background: '#F5ECD2', marginLeft: '-48px', marginRight: '-48px', marginBottom: '-66px', marginTop: '60px' }}>
        <div style={{ position: 'relative', minHeight: '380px', background: 'linear-gradient(135deg,#dfe8ea,#c8dce0)', overflow: 'hidden' }}>
          
          {mapEnabled ? (
            <MapWidget destination={itinerary.destination} markers={markers} />
          ) : (
            <>
              <div style={{ position: 'absolute', inset: 0, background: 'repeating-linear-gradient(0deg,rgba(21,112,172,.08) 0 1px,transparent 1px 46px),repeating-linear-gradient(90deg,rgba(21,112,172,.08) 0 1px,transparent 1px 46px)' }}></div>
              <div style={{ position: 'absolute', inset: 0, background: 'radial-gradient(60% 50% at 30% 40%,rgba(44,159,199,.25),transparent 60%),radial-gradient(50% 40% at 75% 70%,rgba(16,185,129,.2),transparent 60%)' }}></div>
              
              <svg viewBox="0 0 500 380" style={{ position: 'absolute', inset: 0, width: '100%', height: '100%' }}>
                <path d="M90 300 C 160 240, 130 160, 220 150 S 360 120, 400 70" fill="none" stroke="#F06B04" strokeWidth="3" strokeDasharray="2 10" strokeLinecap="round" />
              </svg>
              
              {[
                { x: '18%', y: '80%', label: 'Start' },
                { x: '44%', y: '40%', label: 'Place 1' },
                { x: '80%', y: '18%', label: 'Hotel' }
              ].map((pn, i) => (
                <div key={i} style={{ position: 'absolute', left: pn.x, top: pn.y, transform: 'translate(-50%,-100%)', display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
                  <div style={{ background: '#12241d', color: '#F5ECD2', fontFamily: '"DM Sans", sans-serif', fontWeight: 600, fontSize: '11px', padding: '4px 9px', borderRadius: '8px', whiteSpace: 'nowrap', marginBottom: '5px' }}>{pn.label}</div>
                  <div style={{ width: '16px', height: '16px', borderRadius: '50%', background: '#F06B04', border: '3px solid #fff', boxShadow: '0 4px 10px rgba(0,0,0,.3)' }}></div>
                </div>
              ))}
              
              <div style={{ position: 'absolute', left: '20px', bottom: '18px', display: 'flex', alignItems: 'center', gap: '9px', background: 'rgba(255,255,255,.92)', border: '1px solid rgba(0,0,0,.1)', padding: '9px 14px', borderRadius: '10px', fontFamily: '"DM Sans", sans-serif', fontWeight: 500, fontSize: '12px', color: '#6b5b45', maxWidth: '300px' }}>
                <span style={{ fontSize: '15px' }}>🌐</span> Map loads online tiles — everything else runs offline on your device.
              </div>
            </>
          )}

        </div>
        <div style={{ padding: '44px 40px', background: '#12241d', color: '#F5ECD2', display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
          <div style={{ fontFamily: '"DM Sans", sans-serif', fontWeight: 600, fontSize: '12px', letterSpacing: '.18em', textTransform: 'uppercase', color: '#FBB728' }}>Route map</div>
          <h2 style={{ fontFamily: '"Yeseva One", serif', fontWeight: 400, fontSize: '34px', margin: '8px 0 14px' }}>See your route on the map</h2>
          <p style={{ fontFamily: '"DM Sans", sans-serif', fontWeight: 400, fontSize: '15px', lineHeight: 1.6, color: 'rgba(245,236,210,.72)', margin: '0 0 22px', textWrap: 'pretty' }}>
            All activities are pinned on the map. The map is an optional layer — turn it off and the app continues to run fully offline.
          </p>
          <div 
            style={{ display: 'flex', alignItems: 'center', gap: '12px', background: 'rgba(245,236,210,.06)', border: '1px solid rgba(245,236,210,.14)', padding: '14px 16px', borderRadius: '12px', cursor: 'pointer', transition: 'background 0.2s' }}
            onClick={() => setMapEnabled(!mapEnabled)}
          >
            <div style={{ width: '40px', height: '22px', borderRadius: '9999px', background: mapEnabled ? '#10B981' : 'rgba(245,236,210,.2)', position: 'relative', flex: 'none', transition: 'background 0.3s' }}>
              <span style={{ position: 'absolute', right: mapEnabled ? '2px' : 'auto', left: mapEnabled ? 'auto' : '2px', top: '2px', width: '18px', height: '18px', borderRadius: '50%', background: '#fff', transition: 'all 0.3s' }}></span>
            </div>
            <div>
              <div style={{ fontFamily: '"DM Sans", sans-serif', fontWeight: 600, fontSize: '14px' }}>{mapEnabled ? 'Disable map' : 'Enable map'}</div>
              <div style={{ fontFamily: '"DM Sans", sans-serif', fontWeight: 400, fontSize: '12px', color: 'rgba(245,236,210,.55)' }}>OpenStreetMap tiles are loaded online</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
