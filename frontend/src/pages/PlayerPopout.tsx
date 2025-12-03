/**
 * Player Pop-out Page
 * 
 * Dedicated page for the pop-out player window.
 * Reads initial state from URL parameters and renders the PopoutPlayer component.
 * 
 * @author Audiobooker Team
 * @version 1.0.0
 */

import { useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import PopoutPlayer from '@/components/audiobook/PopoutPlayer'
import { AudioState } from '@/hooks/useAudioSync'

export default function PlayerPopout() {
  const [searchParams] = useSearchParams()
  const [initialState, setInitialState] = useState<AudioState | undefined>()
  const [isReady, setIsReady] = useState(false)
  
  useEffect(() => {
    // Parse initial state from URL
    const stateParam = searchParams.get('state')
    
    if (stateParam) {
      try {
        const state = JSON.parse(decodeURIComponent(stateParam)) as AudioState
        setInitialState(state)
      } catch (error) {
        console.error('Failed to parse initial state:', error)
      }
    }
    
    setIsReady(true)
    
    // Set window title
    document.title = 'Audiobooker - Pop-out Player'
  }, [searchParams])
  
  // Update document title when we have the audiobook title
  useEffect(() => {
    if (initialState?.title) {
      document.title = `${initialState.title} - Audiobooker`
    }
  }, [initialState?.title])
  
  if (!isReady) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="animate-pulse text-muted-foreground">Loading...</div>
      </div>
    )
  }
  
  return <PopoutPlayer initialState={initialState} />
}
