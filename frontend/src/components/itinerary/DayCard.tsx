import { useState, useEffect } from 'react'
import type { Day } from '../../types/itinerary'
import { DayEditor } from './DayEditor'
import { useUpdateDay } from '../../hooks/useUpdateDay'
import { useRegenerateDay } from '../../hooks/useRegenerateDay'

const TIME_SLOTS: { key: 'morning' | 'afternoon' | 'evening'; label: string }[] = [
  { key: 'morning',   label: 'Morning' },
  { key: 'afternoon', label: 'Afternoon' },
  { key: 'evening',   label: 'Evening' },
]

interface DayCardProps {
  day: Day
  index: number
  destination?: string
  itineraryId: string
}

function mapsUrl(location: string, destination?: string): string {
  const query = destination ? `${location}, ${destination}` : location
  return `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(query)}`
}

export function DayCard({ day: initialDay, index, destination, itineraryId }: DayCardProps) {
  const [day, setDay] = useState(initialDay)
  const [isEditing, setIsEditing] = useState(false)
  
  const { update, isUpdating, error: updateError } = useUpdateDay()
  const { regenerate, abort, isRegenerating, currentStage, error: regenError, regeneratedDay } = useRegenerateDay()

  useEffect(() => {
    
    return () => abort()
  }, [abort])

  useEffect(() => {
    if (regeneratedDay) {
      setDay(regeneratedDay)
    }
  }, [regeneratedDay])

  const handleSave = async (updatedDay: Day) => {
    try {
      await update(itineraryId, day.day_number, updatedDay)
      setDay(updatedDay)
      setIsEditing(false)
    } catch (e) {
      
    }
  }

  const handleRegenerate = () => {
    regenerate(itineraryId, day.day_number)
  }

  return (
    <div style={{ display: 'flex', flexDirection: index % 2 === 0 ? 'row' : 'row-reverse', alignItems: 'flex-start', justifyContent: 'center', marginBottom: '60px', position: 'relative', width: '100%', gap: '40px' }}>

      <div style={{ position: 'absolute', left: '50%', transform: 'translateX(-50%)', top: '24px', zIndex: 2 }}>
        <div style={{ width: '56px', height: '56px', borderRadius: '50%', background: '#F06B04', color: '#fff', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', boxShadow: '0 0 0 6px rgba(240,107,4,.18)' }}>
          <span style={{ fontFamily: '"DM Sans", sans-serif', fontWeight: 600, fontSize: '8px', letterSpacing: '.1em' }}>DAY</span>
          <span style={{ fontFamily: '"Yeseva One", serif', fontSize: '20px', lineHeight: 0.9 }}>{day.day_number}</span>
        </div>
      </div>

      <div style={{ width: 'calc(50% - 80px)', display: 'flex', justifyContent: index % 2 === 0 ? 'flex-end' : 'flex-start' }}>
        <div style={{ width: '100%', maxWidth: '400px', borderRadius: '16px', overflow: 'hidden', background: 'rgba(245,236,210,.06)', border: '1px solid rgba(245,236,210,.14)', textAlign: 'left' }}>
          
          <div style={{ height: '150px', background: 'linear-gradient(180deg, rgba(0,0,0,0) 0%, rgba(0,0,0,0.7) 100%), #2a4a3c', position: 'relative' }}>
            <div style={{ position: 'absolute', left: '16px', bottom: '16px', right: '16px', fontFamily: '"Yeseva One", serif', fontStyle: 'italic', fontSize: '18px', color: '#F5ECD2', textShadow: '0 2px 12px rgba(0,0,0,.8)', display: '-webkit-box', WebkitLineClamp: 3, WebkitBoxOrient: 'vertical', overflow: 'hidden', lineHeight: 1.3 }}>
              {day.title || `Day ${day.day_number}`}
            </div>
            
            <div className="no-print" style={{ position: 'absolute', right: '14px', top: '14px', display: 'flex', gap: '8px' }}>
              {!isEditing && !isRegenerating && (
                <>
                  <button onClick={() => setIsEditing(true)} style={{ background: 'rgba(0,0,0,0.5)', color: '#fff', border: '1px solid rgba(255,255,255,0.3)', padding: '4px 8px', borderRadius: '4px', cursor: 'pointer', fontSize: '11px', fontWeight: 'bold' }}>Edit</button>
                  <button onClick={handleRegenerate} style={{ background: 'rgba(0,0,0,0.5)', color: '#fff', border: '1px solid rgba(255,255,255,0.3)', padding: '4px 8px', borderRadius: '4px', cursor: 'pointer', fontSize: '11px', fontWeight: 'bold' }}>
                    Regenerate
                  </button>
                </>
              )}
              {isRegenerating && (
                <button onClick={abort} style={{ background: 'rgba(255,0,0,0.5)', color: '#fff', border: '1px solid rgba(255,255,255,0.3)', padding: '4px 8px', borderRadius: '4px', cursor: 'pointer', fontSize: '11px', fontWeight: 'bold' }}>
                  Cancel
                </button>
              )}
            </div>
          </div>
          
          {regenError && (
             <div role="alert" style={{ padding: '12px', background: 'rgba(255,0,0,0.1)', color: '#ff6b6b', fontSize: '12px', borderBottom: '1px solid rgba(245,236,210,.14)' }}>
               Regeneration error: {regenError}
             </div>
          )}

          {isRegenerating ? (
            <div style={{ padding: '40px 20px', textAlign: 'center' }}>
              <div style={{ display: 'inline-block', width: '24px', height: '24px', border: '3px solid rgba(240,107,4,0.3)', borderRadius: '50%', borderTopColor: '#F06B04', animation: 'spin 1s linear infinite' }} />
              <div style={{ marginTop: '16px', fontFamily: '"DM Sans", sans-serif', fontSize: '13px', color: 'rgba(245,236,210,.7)' }}>
                Regenerating day...
              </div>
              <div style={{ marginTop: '4px', fontFamily: '"DM Sans", sans-serif', fontSize: '11px', color: '#2C9FC7', fontWeight: 'bold' }}>
                {currentStage}
              </div>
            </div>
          ) : isEditing ? (
            <DayEditor 
              day={day} 
              onSave={handleSave} 
              onCancel={() => setIsEditing(false)} 
              isSaving={isUpdating} 
              error={updateError}
            />
          ) : (
            <div style={{ padding: '18px 20px 20px' }}>
              
              <div style={{ marginTop: '14px', display: 'flex', flexDirection: 'column', gap: '10px' }}>
                {TIME_SLOTS.map(({ key, label }) => {
                  const slot = day[key]
                  if (!slot?.description) return null
                  return (
                    <div key={key} style={{ display: 'flex', gap: '12px', alignItems: 'flex-start' }}>
                      <div style={{ flex: 'none', width: '64px', fontFamily: '"DM Sans", sans-serif', fontWeight: 700, fontSize: '11px', color: '#2C9FC7', textTransform: 'uppercase', letterSpacing: '.06em', paddingTop: '2px' }}>
                        {label}
                      </div>
                      <div style={{ flex: 1 }}>
                        <div style={{ fontFamily: '"DM Sans", sans-serif', fontWeight: 400, fontSize: '13px', lineHeight: 1.45, color: 'rgba(245,236,210,.7)', marginTop: '2px' }}>
                          {slot.description}
                        </div>
                        
                        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', marginTop: '8px' }}>
                          {slot.location && (
                            <a href={mapsUrl(slot.location, destination)} target="_blank" rel="noopener noreferrer" style={{ textDecoration: 'none', fontFamily: '"DM Sans", sans-serif', fontWeight: 500, fontSize: '11px', color: 'rgba(245,236,210,.8)', background: 'rgba(245,236,210,.09)', border: '1px solid rgba(245,236,210,.14)', padding: '3px 9px', borderRadius: '9999px' }}>
                              {slot.location}
                            </a>
                          )}
                          {slot.duration_estimate && (
                            <span style={{ fontFamily: '"DM Sans", sans-serif', fontWeight: 500, fontSize: '11px', color: 'rgba(245,236,210,.8)', background: 'rgba(245,236,210,.09)', border: '1px solid rgba(245,236,210,.14)', padding: '3px 9px', borderRadius: '9999px' }}>
                              {slot.duration_estimate}
                            </span>
                          )}
                          {slot.cost_estimate && (
                            <span style={{ fontFamily: '"DM Sans", sans-serif', fontWeight: 500, fontSize: '11px', color: 'rgba(245,236,210,.8)', background: 'rgba(245,236,210,.09)', border: '1px solid rgba(245,236,210,.14)', padding: '3px 9px', borderRadius: '9999px' }}>
                              {slot.cost_estimate}
                            </span>
                          )}
                        </div>
                      </div>
                    </div>
                  )
                })}
              </div>

              {(day.meals.breakfast || day.meals.lunch || day.meals.dinner) && (
                <div style={{ marginTop: '20px', paddingTop: '20px', borderTop: '1px solid rgba(245,236,210,.14)' }}>
                  <div style={{ fontFamily: '"DM Sans", sans-serif', fontWeight: 600, fontSize: '12px', color: '#FBB728', letterSpacing: '.05em', marginBottom: '10px' }}>Yemekler</div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                    {(['breakfast', 'lunch', 'dinner'] as const).map((meal) => {
                      const text = day.meals[meal]
                      if (!text) return null
                      return (
                        <div key={meal} style={{ display: 'flex', gap: '12px', alignItems: 'flex-start' }}>
                          <div style={{ flex: 'none', width: '64px', fontFamily: '"DM Sans", sans-serif', fontWeight: 700, fontSize: '11px', color: '#2C9FC7', textTransform: 'uppercase', letterSpacing: '.06em', paddingTop: '2px' }}>
                            {meal}
                          </div>
                          <div style={{ flex: 1, fontFamily: '"DM Sans", sans-serif', fontWeight: 400, fontSize: '13px', lineHeight: 1.45, color: 'rgba(245,236,210,.7)' }}>
                            {text}
                          </div>
                        </div>
                      )
                    })}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      <div style={{ width: 'calc(50% - 80px)' }}></div>
      <style>{`
        @keyframes spin {
          0% { transform: rotate(0deg); }
          100% { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  )
}
