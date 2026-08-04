

import type { HealthStatus, Itinerary, ItinerarySummary, SSEEvent, TripRequest, Day } from '../types/itinerary'

const BASE = '/api/v1'

export async function getHealth(): Promise<HealthStatus> {
  const res = await fetch(`${BASE}/health`)
  if (!res.ok) throw new Error(`Health check failed: ${res.status}`)
  return res.json()
}

export async function* streamGenerate(
  request: TripRequest,
  signal?: AbortSignal,
): AsyncGenerator<SSEEvent> {
  const res = await fetch(`${BASE}/generate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
    signal,
  })

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Unknown error' }))
    throw new Error(err.detail || `Generation failed: ${res.status}`)
  }

  const reader = res.body?.getReader()
  if (!reader) throw new Error('No response body')

  const decoder = new TextDecoder()
  let buffer = ''

  try {
    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() ?? ''   

      for (const line of lines) {
        const trimmed = line.trim()
        if (!trimmed.startsWith('data:')) continue
        const jsonStr = trimmed.slice(5).trim()
        if (!jsonStr) continue
        try {
          yield JSON.parse(jsonStr) as SSEEvent
        } catch {
          
        }
      }
    }
  } finally {
    reader.releaseLock()
  }
}

export async function* streamRegenerateDay(
  itineraryId: string,
  dayNumber: number,
  signal?: AbortSignal,
): AsyncGenerator<SSEEvent> {
  const res = await fetch(`${BASE}/itineraries/${itineraryId}/days/${dayNumber}/regenerate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ reason: 'User requested regeneration' }),
    signal,
  })

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Unknown error' }))
    throw new Error(err.detail || `Regeneration failed: ${res.status}`)
  }

  const reader = res.body?.getReader()
  if (!reader) throw new Error('No response body')

  const decoder = new TextDecoder()
  let buffer = ''

  try {
    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() ?? ''

      for (const line of lines) {
        const trimmed = line.trim()
        if (!trimmed.startsWith('data:')) continue
        const jsonStr = trimmed.slice(5).trim()
        if (!jsonStr) continue
        try {
          yield JSON.parse(jsonStr) as SSEEvent
        } catch {
          
        }
      }
    }
  } finally {
    reader.releaseLock()
  }
}

export async function getItineraries(limit = 50): Promise<ItinerarySummary[]> {
  const res = await fetch(`${BASE}/itineraries?limit=${limit}`)
  if (!res.ok) throw new Error(`Failed to fetch itineraries: ${res.status}`)
  return res.json()
}

export async function getItinerary(id: string): Promise<Itinerary> {
  const res = await fetch(`${BASE}/itineraries/${id}`)
  if (!res.ok) throw new Error(`Itinerary not found: ${id}`)
  return res.json()
}

export async function exportItinerary(
  id: string,
  fmt: 'json' | 'md',
): Promise<void> {
  const res = await fetch(`${BASE}/itineraries/${id}/export?fmt=${fmt}`)
  if (!res.ok) throw new Error(`Export failed: ${res.status}`)

  const blob = await res.blob()
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = res.headers.get('Content-Disposition')?.match(/filename="([^"]+)"/)?.[1]
    ?? `itinerary.${fmt}`
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}

export async function updateDay(
  itineraryId: string,
  dayNumber: number,
  dayData: Day,
): Promise<void> {
  const res = await fetch(`${BASE}/itineraries/${itineraryId}/days/${dayNumber}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(dayData),
  })
  if (!res.ok) throw new Error(`Failed to update day ${dayNumber}: ${res.status}`)
}

export function openItineraryHTML(id: string): void {
  window.open(`${BASE}/itineraries/${id}/export?fmt=html`, '_blank', 'noopener,noreferrer')
}
