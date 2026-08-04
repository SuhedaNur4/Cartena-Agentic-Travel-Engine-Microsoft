import { useCallback, useRef } from 'react'
import { streamGenerate } from '../services/api'
import { useItineraryStore } from '../store/itineraryStore'
import type { TripRequest } from '../types/itinerary'

export function useGenerateItinerary() {
  const abortRef = useRef<AbortController | null>(null)
  const store = useItineraryStore()

  const generate = useCallback(async (request: TripRequest) => {
    
    abortRef.current?.abort()
    abortRef.current = new AbortController()

    store.startGeneration()

    try {
      let finalId: string | null = null

      for await (const event of streamGenerate(request, abortRef.current.signal)) {
        if (event.type === 'stage') {
          store.setStage(event.name)
        } else if (event.type === 'context') {
          store.setContext(event.kb_chunks, event.kb_miss)
        } else if (event.type === 'chunk') {
          store.appendChunk(event.content)
        } else if (event.type === 'quality_report') {
          store.setQualityWarnings(event.warnings)
        } else if (event.type === 'done') {
          if (event.id) finalId = event.id
        } else if (event.type === 'error') {
          store.setError(event.message)
          return
        }
      }

      if (finalId) {
        store.completeGeneration(finalId)
      }
    } catch (err) {
      if ((err as Error).name !== 'AbortError') {
        store.setError(err instanceof Error ? err.message : 'Generation failed')
      }
    }
  }, [store])

  const cancel = useCallback(() => {
    abortRef.current?.abort()
    store.resetGeneration()
  }, [store])

  return {
    generate,
    cancel,
    isGenerating: store.isGenerating,
    streamedText: store.streamedText,
    generatedId: store.generatedId,
    kbMiss: store.kbMiss,
    kbChunks: store.kbChunks,
    currentStage: store.currentStage,
    qualityWarnings: store.qualityWarnings,
    error: store.error,
  }
}
