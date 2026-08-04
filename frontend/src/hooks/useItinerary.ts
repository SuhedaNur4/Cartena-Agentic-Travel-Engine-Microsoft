import { useState, useEffect } from 'react'
import { getItinerary } from '../services/api'
import type { Itinerary } from '../types/itinerary'

interface UseItineraryResult {
  itinerary: Itinerary | null
  loading: boolean
  error: string | null
}

export function useItinerary(id: string | undefined): UseItineraryResult {
  const [itinerary, setItinerary] = useState<Itinerary | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!id) {
      setLoading(false)
      setError('No itinerary ID provided.')
      return
    }

    let cancelled = false
    setLoading(true)
    setError(null)

    getItinerary(id)
      .then((data) => {
        if (!cancelled) {
          setItinerary(data)
          setLoading(false)
        }
      })
      .catch((err) => {
        if (!cancelled) {
          console.error('Failed to load itinerary:', err)
          setError('Could not load this itinerary.')
          setLoading(false)
        }
      })

    return () => { cancelled = true }
  }, [id])

  return { itinerary, loading, error }
}
