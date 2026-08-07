import { useState } from 'react'
import type { BudgetLevel, Interest, TripRequest } from '../../types/itinerary'
import { Alert } from '../ui/Alert'

const INTERESTS: { value: Interest; label: string }[] = [
  { value: 'culture',    label: 'Culture' },
  { value: 'food',       label: 'Food & Dining' },
  { value: 'adventure',  label: 'Adventure' },
  { value: 'relaxation', label: 'Relaxation' },
  { value: 'shopping',   label: 'Shopping' },
  { value: 'nature',     label: 'Nature' },
  { value: 'nightlife',  label: 'Nightlife' },
]

const BUDGETS: { value: BudgetLevel; label: string; desc: string }[] = [
  { value: 'low',    label: 'Budget',    desc: 'Hostels, street food' },
  { value: 'medium', label: 'Mid-range', desc: '3-star hotels, local restaurants' },
  { value: 'high',   label: 'Luxury',    desc: '5-star hotels, fine dining' },
  { value: 'luxury', label: 'Ultra',     desc: 'No compromise' },
]

interface TripFormProps {
  onGenerate: (request: TripRequest) => void
  isGenerating: boolean
  onCancel: () => void
  engineOffline?: boolean
  initialDestination?: string
}

const inputStyle: React.CSSProperties = {
  width: '100%',
  padding: '14px 18px',
  borderRadius: '12px',
  border: '1px solid rgba(36,26,16,0.15)',
  background: '#fff',
  color: '#241a10',
  fontFamily: '"DM Sans", sans-serif',
  fontSize: '15px',
  outline: 'none',
  boxShadow: 'inset 0 2px 4px rgba(0,0,0,0.02)',
}

const labelStyle: React.CSSProperties = {
  display: 'block',
  fontFamily: '"DM Sans", sans-serif',
  fontWeight: 600,
  fontSize: '13px',
  color: '#8c7e6c',
  textTransform: 'uppercase',
  letterSpacing: '0.05em',
  marginBottom: '8px'
}

export function TripForm({ onGenerate, isGenerating, onCancel, engineOffline = false, initialDestination = '' }: TripFormProps) {
  const [destination, setDestination] = useState(initialDestination)
  const [duration, setDuration] = useState(7)
  const [budget, setBudget] = useState<BudgetLevel>('medium')
  const [interests, setInterests] = useState<Interest[]>(['culture', 'food'])
  const [notes, setNotes] = useState('')
  const [startDate, setStartDate] = useState('')
  const [arrivalCity, setArrivalCity] = useState('')
  const [departureCity, setDepartureCity] = useState('')
  const [errors, setErrors] = useState<Record<string, string>>({})

  const toggleInterest = (interest: Interest) => {
    setInterests((prev) =>
      prev.includes(interest) ? prev.filter((i) => i !== interest) : [...prev, interest]
    )
  }

  const adjustDuration = (delta: number) =>
    setDuration((prev) => Math.max(1, Math.min(30, prev + delta)))

  const handleDurationInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = parseInt(e.target.value, 10)
    if (!isNaN(val)) setDuration(Math.max(1, Math.min(30, val)))
  }

  const validate = (): boolean => {
    const e: Record<string, string> = {}
    if (!destination.trim()) e.destination = 'Destination is required.'
    if (interests.length === 0) e.interests = 'Select at least one interest.'
    setErrors(e)
    return Object.keys(e).length === 0
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!validate()) return
    onGenerate({
      destination: destination.trim(),
      duration_days: duration,
      budget,
      interests,
      notes: notes.trim(),
      start_date: startDate || undefined,
      flight_context: (arrivalCity.trim() || departureCity.trim()) ? {
        arrival_city: arrivalCity.trim() || undefined,
        departure_city: departureCity.trim() || undefined
      } : undefined
    })
  }

  const isDisabled = isGenerating || engineOffline

  return (
    <form onSubmit={handleSubmit} noValidate>
      <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>

        <div>
          <label style={labelStyle} htmlFor="destination">Destination</label>
          <input
            id="destination"
            type="text"
            placeholder="Tokyo, Paris, Bali…"
            value={destination}
            onChange={(e) => setDestination(e.target.value)}
            disabled={isDisabled}
            autoComplete="off"
            autoFocus
            style={{ ...inputStyle, borderColor: errors.destination ? '#F06B04' : 'rgba(36,26,16,0.15)' }}
          />
        </div>

        <div>
          <label style={labelStyle} htmlFor="duration">Duration</label>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <button
              type="button"
              aria-label="Decrease duration"
              onClick={() => adjustDuration(-1)}
              disabled={isDisabled || duration <= 1}
              style={{ width: 44, height: 44, borderRadius: '12px', border: '1px solid rgba(36,26,16,0.15)', background: '#fff', color: '#241a10', fontSize: '20px', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center' }}
            >−</button>
            <input
              id="duration"
              type="number"
              min={1}
              max={30}
              value={duration}
              onChange={handleDurationInput}
              disabled={isDisabled}
              style={{ width: 60, height: 44, textAlign: 'center', background: '#fff', border: '1px solid rgba(36,26,16,0.15)', borderRadius: '12px', fontFamily: '"DM Sans", sans-serif', fontSize: '16px', fontWeight: 600, color: '#241a10', outline: 'none' }}
            />
            <span style={{ fontSize: '15px', color: '#8c7e6c', fontFamily: '"DM Sans", sans-serif' }}>
              {duration === 1 ? 'day' : 'days'}
            </span>
            <div style={{ flex: 1 }} />
            <button
              type="button"
              aria-label="Increase duration"
              onClick={() => adjustDuration(1)}
              disabled={isDisabled || duration >= 30}
              style={{ width: 44, height: 44, borderRadius: '12px', border: '1px solid rgba(36,26,16,0.15)', background: '#fff', color: '#241a10', fontSize: '20px', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center' }}
            >+</button>
          </div>
        </div>

        <div>
          <div style={{ display: 'flex', alignItems: 'baseline', gap: '8px' }}>
            <label style={labelStyle} htmlFor="start-date">Trip Start Date</label>
            <span style={{ fontSize: '12px', color: '#b5a593', fontFamily: '"DM Sans", sans-serif' }}>optional · enables weather forecast</span>
          </div>
          <input
            id="start-date"
            type="date"
            value={startDate}
            onChange={(e) => setStartDate(e.target.value)}
            disabled={isDisabled}
            min={new Date().toISOString().split('T')[0]}
            style={inputStyle}
          />
        </div>

        <div style={{ display: 'flex', gap: '16px' }}>
          <div style={{ flex: 1 }}>
            <div style={{ display: 'flex', alignItems: 'baseline', gap: '8px' }}>
              <label style={labelStyle} htmlFor="arrival-city">Arrival City</label>
              <span style={{ fontSize: '12px', color: '#b5a593', fontFamily: '"DM Sans", sans-serif' }}>optional</span>
            </div>
            <input
              id="arrival-city"
              type="text"
              placeholder="e.g. Tokyo"
              value={arrivalCity}
              onChange={(e) => setArrivalCity(e.target.value)}
              disabled={isDisabled}
              style={inputStyle}
            />
          </div>
          <div style={{ flex: 1 }}>
            <div style={{ display: 'flex', alignItems: 'baseline', gap: '8px' }}>
              <label style={labelStyle} htmlFor="departure-city">Departure City</label>
              <span style={{ fontSize: '12px', color: '#b5a593', fontFamily: '"DM Sans", sans-serif' }}>optional</span>
            </div>
            <input
              id="departure-city"
              type="text"
              placeholder="e.g. Osaka"
              value={departureCity}
              onChange={(e) => setDepartureCity(e.target.value)}
              disabled={isDisabled}
              style={inputStyle}
            />
          </div>
        </div>

        <div>
          <label style={labelStyle}>Budget</label>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
            {BUDGETS.map((b) => (
              <button
                key={b.value}
                type="button"
                onClick={() => setBudget(b.value)}
                disabled={isDisabled}
                title={b.desc}
                style={{
                  padding: '10px 18px',
                  borderRadius: '9999px',
                  border: budget === b.value ? 'none' : '1px solid rgba(36,26,16,0.1)',
                  background: budget === b.value ? '#2C9FC7' : 'rgba(36,26,16,0.04)',
                  color: budget === b.value ? '#fff' : '#8c7e6c',
                  fontFamily: '"DM Sans", sans-serif',
                  fontWeight: 600,
                  fontSize: '14px',
                  cursor: 'pointer',
                  transition: 'all 0.2s'
                }}
              >
                {b.label}
              </button>
            ))}
          </div>
        </div>

        <div>
          <label style={labelStyle}>Interests</label>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
            {INTERESTS.map((interest) => (
              <button
                key={interest.value}
                type="button"
                onClick={() => toggleInterest(interest.value)}
                disabled={isDisabled}
                style={{
                  padding: '10px 18px',
                  borderRadius: '9999px',
                  border: interests.includes(interest.value) ? 'none' : '1px solid rgba(36,26,16,0.1)',
                  background: interests.includes(interest.value) ? '#F06B04' : 'rgba(36,26,16,0.04)',
                  color: interests.includes(interest.value) ? '#fff' : '#8c7e6c',
                  fontFamily: '"DM Sans", sans-serif',
                  fontWeight: 600,
                  fontSize: '14px',
                  cursor: 'pointer',
                  transition: 'all 0.2s'
                }}
              >
                {interest.label}
              </button>
            ))}
          </div>
        </div>

        <div>
          <div style={{ display: 'flex', alignItems: 'baseline', gap: '8px' }}>
            <label style={labelStyle} htmlFor="notes">Anything else?</label>
            <span style={{ fontSize: '12px', color: '#b5a593', fontFamily: '"DM Sans", sans-serif' }}>optional</span>
          </div>
          <textarea
            id="notes"
            placeholder="e.g. Vegetarian only, pet-friendly travel, we have a rental car, prefer hidden cafés away from tourists."
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            disabled={isDisabled}
            rows={4}
            style={{ ...inputStyle, resize: 'vertical' }}
          />
        </div>

        {engineOffline && (
          <Alert type="warning" title="AI Engine Not Running" message="Start the AI engine to generate itineraries." />
        )}

        <div style={{ display: 'flex', gap: '16px', marginTop: '8px' }}>
          <button
            type="submit"
            disabled={isDisabled}
            style={{
              flex: 1,
              padding: '18px 24px',
              borderRadius: '9999px',
              border: 'none',
              background: '#241a10',
              color: '#F5ECD2',
              fontFamily: '"DM Sans", sans-serif',
              fontWeight: 600,
              fontSize: '16px',
              cursor: isDisabled ? 'not-allowed' : 'pointer',
              opacity: isDisabled ? 0.7 : 1,
              boxShadow: '0 12px 24px -10px rgba(36,26,16,0.5)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '8px'
            }}
          >
            {isGenerating ? 'Generating…' : 'Generate Itinerary'}
          </button>
          
          {isGenerating && (
            <button
              type="button"
              onClick={onCancel}
              style={{
                padding: '18px 32px',
                borderRadius: '9999px',
                border: '1px solid rgba(36,26,16,0.2)',
                background: 'transparent',
                color: '#241a10',
                fontFamily: '"DM Sans", sans-serif',
                fontWeight: 600,
                fontSize: '16px',
                cursor: 'pointer'
              }}
            >
              Cancel
            </button>
          )}
        </div>

      </div>
    </form>
  )
}
