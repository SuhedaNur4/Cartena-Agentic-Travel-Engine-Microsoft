import { useState, useRef, useCallback } from 'react'
import { streamRegenerateDay } from '../services/api'
import type { Day } from '../types/itinerary'

interface UseRegenerateDayResult {
  regenerate: (itineraryId: string, dayNumber: number) => Promise<void>
  abort: () => void
  isRegenerating: boolean
  streamedText: string
  currentStage: string
  error: string | null
  regeneratedDay: Day | null
}

export function useRegenerateDay(): UseRegenerateDayResult {
  const [isRegenerating, setIsRegenerating] = useState(false)
  const [streamedText, setStreamedText] = useState('')
  const [currentStage, setCurrentStage] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [regeneratedDay, setRegeneratedDay] = useState<Day | null>(null)
  
  const abortControllerRef = useRef<AbortController | null>(null)

  const abort = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort()
      abortControllerRef.current = null
      setIsRegenerating(false)
    }
  }, [])

  const regenerate = async (itineraryId: string, dayNumber: number) => {
    abort() 
    
    setIsRegenerating(true)
    setStreamedText('')
    setCurrentStage('')
    setError(null)
    setRegeneratedDay(null)

    const controller = new AbortController()
    abortControllerRef.current = controller

    try {
      for await (const event of streamRegenerateDay(itineraryId, dayNumber, controller.signal)) {
        if (event.type === 'stage') {
          setCurrentStage(event.name)
        } else if (event.type === 'chunk') {
          setStreamedText((prev) => prev + event.content)
        } else if (event.type === 'done') {
          if (event.day) {
            setRegeneratedDay(event.day)
          }
          setIsRegenerating(false)
        } else if (event.type === 'error') {
          setError(event.message)
          setIsRegenerating(false)
        }
      }
    } catch (err: any) {
      if (err.name === 'AbortError') {
        console.log('Regeneration aborted by user')
      } else {
        setError(err.message || 'Failed to regenerate day')
        setIsRegenerating(false)
      }
    } finally {
      abortControllerRef.current = null
    }
  }

  return { regenerate, abort, isRegenerating, streamedText, currentStage, error, regeneratedDay }
}
