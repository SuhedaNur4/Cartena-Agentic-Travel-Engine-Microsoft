import { useEffect } from 'react'
import { getHealth } from '../services/api'
import { useSystemStore } from '../store/systemStore'

export function useHealthCheck() {
  const { setHealth, setHealthLoading } = useSystemStore()

  useEffect(() => {
    let cancelled = false

    const check = async () => {
      setHealthLoading(true)
      try {
        const health = await getHealth()
        if (!cancelled) setHealth(health)
      } catch {
        if (!cancelled) {
          setHealth({
            status: 'offline',
            llm: 'offline',
            embedding: 'offline',
            chroma: 'not_ready',
            kb_document_count: 0,
            llm_model: 'unknown',
            embedding_model: 'unknown',
          })
        }
      }
    }

    check()
    const interval = setInterval(check, 30_000)  

    return () => {
      cancelled = true
      clearInterval(interval)
    }
  }, [setHealth, setHealthLoading])

  return useSystemStore((s) => s.health)
}
