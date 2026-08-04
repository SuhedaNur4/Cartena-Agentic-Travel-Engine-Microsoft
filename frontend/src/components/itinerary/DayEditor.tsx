import { useState } from 'react'
import type { Day } from '../../types/itinerary'

interface DayEditorProps {
  day: Day
  onSave: (day: Day) => Promise<void>
  onCancel: () => void
  isSaving: boolean
  error: string | null
}

const TIME_SLOTS = ['morning', 'afternoon', 'evening'] as const

export function DayEditor({ day: initialDay, onSave, onCancel, isSaving, error }: DayEditorProps) {
  const [day, setDay] = useState(initialDay)
  const [validationError, setValidationError] = useState<string | null>(null)

  const handleSaveClick = () => {
    
    if (!day.title.trim()) {
      setValidationError('Day title cannot be empty.')
      return
    }
    const hasAnyActivity = TIME_SLOTS.some(slot => day[slot]?.description?.trim())
    if (!hasAnyActivity) {
      setValidationError('En az bir aktivite açıklaması girmelisiniz (Sabah, Öğle veya Akşam).')
      return
    }
    
    setValidationError(null)
    onSave(day)
  }

  const inputStyle = {
    width: '100%',
    background: 'rgba(0,0,0,0.2)',
    border: '1px solid rgba(255,255,255,0.1)',
    color: '#fff',
    padding: '8px',
    borderRadius: '4px',
    fontFamily: 'inherit',
    fontSize: '13px',
    marginBottom: '8px'
  }

  return (
    <div style={{ padding: '20px', background: 'rgba(0,0,0,0.1)' }}>
      {(error || validationError) && (
        <div role="alert" style={{ color: '#ff6b6b', marginBottom: '16px', fontSize: '13px', background: 'rgba(255,0,0,0.1)', padding: '8px', borderRadius: '4px' }}>
          {error || validationError}
        </div>
      )}

      <div style={{ marginBottom: '16px' }}>
        <label style={{ display: 'block', fontSize: '11px', color: '#2C9FC7', fontWeight: 'bold', marginBottom: '4px' }}>BAŞLIK</label>
        <input 
          value={day.title} 
          onChange={e => setDay({...day, title: e.target.value})}
          style={inputStyle}
          aria-invalid={!day.title.trim()}
        />
      </div>

      {TIME_SLOTS.map((slot) => (
        <div key={slot} style={{ marginBottom: '16px', padding: '12px', background: 'rgba(255,255,255,0.03)', borderRadius: '8px' }}>
          <div style={{ fontSize: '11px', color: '#F06B04', fontWeight: 'bold', textTransform: 'uppercase', marginBottom: '8px' }}>
            {slot === 'morning' ? 'Sabah' : slot === 'afternoon' ? 'Öğle' : 'Akşam'}
          </div>
          
          <label style={{ display: 'block', fontSize: '10px', color: 'rgba(255,255,255,0.5)', marginBottom: '2px' }}>Açıklama</label>
          <textarea 
            value={day[slot].description}
            onChange={e => setDay({...day, [slot]: {...day[slot], description: e.target.value}})}
            style={{ ...inputStyle, minHeight: '60px', resize: 'vertical' }}
          />
          
          <div style={{ display: 'flex', gap: '8px' }}>
            <div style={{ flex: 1 }}>
              <label style={{ display: 'block', fontSize: '10px', color: 'rgba(255,255,255,0.5)', marginBottom: '2px' }}>Lokasyon</label>
              <input 
                value={day[slot].location || ''}
                onChange={e => setDay({...day, [slot]: {...day[slot], location: e.target.value}})}
                style={inputStyle}
              />
            </div>
            <div style={{ flex: 1 }}>
              <label style={{ display: 'block', fontSize: '10px', color: 'rgba(255,255,255,0.5)', marginBottom: '2px' }}>Maliyet</label>
              <input 
                value={day[slot].cost_estimate || ''}
                onChange={e => setDay({...day, [slot]: {...day[slot], cost_estimate: e.target.value}})}
                style={inputStyle}
              />
            </div>
            <div style={{ flex: 1 }}>
              <label style={{ display: 'block', fontSize: '10px', color: 'rgba(255,255,255,0.5)', marginBottom: '2px' }}>Süre</label>
              <input 
                value={day[slot].duration_estimate || ''}
                onChange={e => setDay({...day, [slot]: {...day[slot], duration_estimate: e.target.value}})}
                style={inputStyle}
              />
            </div>
          </div>
        </div>
      ))}

      <div style={{ marginBottom: '16px', padding: '12px', background: 'rgba(255,255,255,0.03)', borderRadius: '8px' }}>
        <div style={{ fontSize: '11px', color: '#FBB728', fontWeight: 'bold', textTransform: 'uppercase', marginBottom: '8px' }}>Yemekler</div>
        {(['breakfast', 'lunch', 'dinner'] as const).map(meal => (
          <div key={meal} style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
            <label style={{ width: '60px', fontSize: '10px', color: 'rgba(255,255,255,0.5)', textTransform: 'capitalize' }}>{meal}</label>
            <input 
              value={day.meals[meal] || ''}
              onChange={e => setDay({...day, meals: {...day.meals, [meal]: e.target.value}})}
              style={{ ...inputStyle, marginBottom: 0 }}
            />
          </div>
        ))}
      </div>

      <div style={{ display: 'flex', gap: '8px', justifyContent: 'flex-end', marginTop: '20px' }}>
        <button 
          onClick={onCancel} 
          disabled={isSaving}
          style={{ background: 'rgba(255,255,255,0.1)', color: '#fff', border: 'none', padding: '8px 16px', borderRadius: '4px', cursor: 'pointer', fontSize: '12px' }}
        >
          İptal
        </button>
        <button 
          onClick={handleSaveClick} 
          disabled={isSaving}
          style={{ background: '#F06B04', color: '#fff', border: 'none', padding: '8px 16px', borderRadius: '4px', cursor: isSaving ? 'not-allowed' : 'pointer', fontSize: '12px', fontWeight: 'bold' }}
        >
          {isSaving ? 'Kaydediliyor...' : 'Kaydet'}
        </button>
      </div>
    </div>
  )
}
