

export type BudgetLevel = 'low' | 'medium' | 'high' | 'luxury'
export type Interest =
  | 'culture'
  | 'food'
  | 'adventure'
  | 'relaxation'
  | 'shopping'
  | 'nature'
  | 'nightlife'

export interface TripRequest {
  destination: string
  duration_days: number
  budget: BudgetLevel
  interests: Interest[]
  notes?: string
  start_date?: string   
}

export interface ActivityBlock {
  description: string
  location: string
  why_recommended?: string
  duration_estimate?: string
  cost_estimate?: string
  reservation_needed?: boolean
  transport_suggestion?: string
  lat?: number
  lon?: number
}

export interface MealSuggestion {
  breakfast: string
  lunch: string
  dinner: string
}

export interface Day {
  day_number: number
  title: string
  morning: ActivityBlock
  afternoon: ActivityBlock
  evening: ActivityBlock
  meals: MealSuggestion
  budget_estimate: BudgetLevel
  tips: string[]
}

export interface Itinerary {
  id: string
  destination: string
  duration_days: number
  budget: BudgetLevel
  interests: Interest[]
  notes: string
  model_used: string
  created_at: string
  days: Day[]
  day_count: number
  is_complete: boolean
  kb_miss?: boolean   
  is_favorite: boolean
}

export interface ItinerarySummary {
  id: string
  destination: string
  duration_days: number
  budget: BudgetLevel
  model_used: string
  created_at: string
  day_count: number
  is_favorite: boolean
}

export interface HealthStatus {
  status: 'healthy' | 'degraded' | 'offline'
  llm: 'online' | 'offline'
  embedding: 'online' | 'offline'
  chroma: 'ready' | 'not_ready'
  kb_document_count: number
  llm_model: string
  embedding_model: string
}

export type SSEEvent =
  | { type: 'stage'; name: string }
  | { type: 'context'; kb_chunks: number; kb_miss: boolean }
  | { type: 'chunk'; content: string }
  | { type: 'done'; id?: string; kb_miss?: boolean; day_count?: number; is_complete?: boolean; day?: Day }
  | { type: 'quality_report'; constraint_score: number; quality_score: number; warnings: string[] }
  | { type: 'error'; message: string }
