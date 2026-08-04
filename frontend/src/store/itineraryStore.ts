import { create } from 'zustand'
import type { ItinerarySummary } from '../types/itinerary'

interface ItineraryState {
  
  isGenerating: boolean
  streamedText: string           
  generatedId: string | null     
  kbMiss: boolean                
  kbChunks: number               
  currentStage: string           
  qualityWarnings: string[]

  history: ItinerarySummary[]
  historyLoading: boolean

  error: string | null

  startGeneration: () => void
  appendChunk: (token: string) => void
  setContext: (kbChunks: number, kbMiss: boolean) => void
  setStage: (stage: string) => void
  setQualityWarnings: (warnings: string[]) => void
  completeGeneration: (id: string) => void
  setError: (message: string) => void
  resetGeneration: () => void
  setHistory: (items: ItinerarySummary[]) => void
  setHistoryLoading: (loading: boolean) => void
}

export const useItineraryStore = create<ItineraryState>((set) => ({
  isGenerating: false,
  streamedText: '',
  generatedId: null,
  kbMiss: false,
  kbChunks: 0,
  currentStage: '',
  qualityWarnings: [],
  history: [],
  historyLoading: false,
  error: null,

  startGeneration: () =>
    set({
      isGenerating: true,
      streamedText: '',
      generatedId: null,
      kbMiss: false,
      kbChunks: 0,
      currentStage: '',
      qualityWarnings: [],
      error: null,
    }),

  appendChunk: (token) =>
    set((state) => ({ streamedText: state.streamedText + token })),

  setContext: (kbChunks, kbMiss) =>
    set({ kbChunks, kbMiss }),

  setStage: (stage) =>
    set({ currentStage: stage }),

  setQualityWarnings: (warnings) =>
    set({ qualityWarnings: warnings }),

  completeGeneration: (id) =>
    set({ isGenerating: false, generatedId: id, currentStage: 'Completed' }),

  setError: (message) =>
    set({ isGenerating: false, error: message }),

  resetGeneration: () =>
    set({
      isGenerating: false,
      streamedText: '',
      generatedId: null,
      kbMiss: false,
      kbChunks: 0,
      currentStage: '',
      qualityWarnings: [],
      error: null,
    }),

  setHistory: (items) => set({ history: items }),
  setHistoryLoading: (loading) => set({ historyLoading: loading }),
}))
