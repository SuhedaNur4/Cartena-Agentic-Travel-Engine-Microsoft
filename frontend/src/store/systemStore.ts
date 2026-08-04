import { create } from 'zustand'
import type { HealthStatus } from '../types/itinerary'

interface SystemState {
  health: HealthStatus | null
  healthLoading: boolean
  setHealth: (health: HealthStatus) => void
  setHealthLoading: (loading: boolean) => void
}

export const useSystemStore = create<SystemState>((set) => ({
  health: null,
  healthLoading: true,
  setHealth: (health) => set({ health, healthLoading: false }),
  setHealthLoading: (loading) => set({ healthLoading: loading }),
}))
