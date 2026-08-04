import { useState } from 'react'
import { updateDay } from '../services/api'
import type { Day } from '../types/itinerary'

interface UseUpdateDayResult {
  update: (itineraryId: string, dayNumber: number, dayData: Day) => Promise<void>
  isUpdating: boolean
  error: string | null
}

export function useUpdateDay(): UseUpdateDayResult {
  const [isUpdating, setIsUpdating] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const update = async (itineraryId: string, dayNumber: number, dayData: Day) => {
    setIsUpdating(true)
    setError(null)
    try {
      await updateDay(itineraryId, dayNumber, dayData)
    } catch (err: any) {
      setError(err.message || 'Failed to update day')
      throw err 
    } finally {
      setIsUpdating(false)
    }
  }

  return { update, isUpdating, error }
}
