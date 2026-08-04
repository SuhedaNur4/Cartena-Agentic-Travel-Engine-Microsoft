import { exportItinerary, openItineraryHTML } from '../../services/api'
import { useState } from 'react'

interface ExportButtonsProps {
  itineraryId: string
}

export function ExportButtons({ itineraryId }: ExportButtonsProps) {
  const [loading, setLoading] = useState<'json' | 'md' | null>(null)

  const handleExport = async (fmt: 'json' | 'md') => {
    setLoading(fmt)
    try {
      await exportItinerary(itineraryId, fmt)
    } catch (err) {
      console.error('Export failed:', err)
    } finally {
      setLoading(null)
    }
  }

  return (
    <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
      
      <button
        className="btn btn-ghost btn-sm"
        onClick={() => openItineraryHTML(itineraryId)}
        id="export-pdf-btn"
        title="Opens a print-ready page. Use File → Print → Save as PDF."
      >
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ marginRight: 4 }}>
          <polyline points="6 9 6 2 18 2 18 9"/>
          <path d="M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2"/>
          <rect x="6" y="14" width="12" height="8"/>
        </svg>
        PDF
      </button>
      <button
        className="btn btn-ghost btn-sm"
        onClick={() => handleExport('md')}
        disabled={loading !== null}
        id="export-markdown-btn"
      >
        {loading === 'md' ? <span className="spinner" /> : null}
        Markdown
      </button>
      <button
        className="btn btn-ghost btn-sm"
        onClick={() => handleExport('json')}
        disabled={loading !== null}
        id="export-json-btn"
      >
        {loading === 'json' ? <span className="spinner" /> : null}
        JSON
      </button>
    </div>
  )
}
