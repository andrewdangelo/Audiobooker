// Custom hook for managing audiobooks

import { useState, useEffect } from 'react'

interface Audiobook {
  id: string
  title: string
  duration?: string
  createdAt: string
}

export function useAudiobooks() {
  const [audiobooks, setAudiobooks] = useState<Audiobook[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const fetchAudiobooks = async () => {
    setLoading(true)
    try {
      // TODO: Implement actual API call
      // const data = await audiobookService.getAll()
      // setAudiobooks(data)
      setAudiobooks([])
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch audiobooks')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchAudiobooks()
  }, [])

  return { audiobooks, loading, error, refetch: fetchAudiobooks }
}
