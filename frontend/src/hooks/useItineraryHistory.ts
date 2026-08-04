import { useCallback, useEffect } from 'react'
import { getItineraries } from '../services/api'
import { useItineraryStore } from '../store/itineraryStore'

export function useItineraryHistory() {
  const { setHistory, setHistoryLoading, history, historyLoading } = useItineraryStore()

  const refresh = useCallback(async () => {
    setHistoryLoading(true)
    try {
      const items = await getItineraries()
      setHistory(items)
    } catch (err) {
      console.error('Failed to fetch history:', err)
    } finally {
      setHistoryLoading(false)
    }
  }, [setHistory, setHistoryLoading])

  useEffect(() => {
    refresh()
  }, [refresh])

  return { history, historyLoading, refresh }
}
