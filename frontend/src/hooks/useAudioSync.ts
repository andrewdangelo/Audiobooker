/**
 * useAudioSync Hook
 * 
 * Manages cross-window audio player synchronization using BroadcastChannel API.
 * Enables communication between main window and pop-out player window.
 * 
 * @author Audiobooker Team
 * @version 1.0.0
 */

import { useEffect, useRef, useCallback, useState } from 'react'

// Channel name for audio player synchronization
const AUDIO_SYNC_CHANNEL = 'audiobooker-audio-sync'

// Message types for cross-window communication
export type AudioSyncMessageType =
  | 'PLAY'
  | 'PAUSE'
  | 'SEEK'
  | 'SPEED_CHANGE'
  | 'TIME_UPDATE'
  | 'METADATA_UPDATE'
  | 'POPOUT_OPENED'
  | 'POPOUT_CLOSED'
  | 'REQUEST_STATE'
  | 'STATE_RESPONSE'

// Audio state that gets synchronized
export interface AudioState {
  isPlaying: boolean
  currentTime: number
  duration: number
  playbackRate: number
  audioUrl?: string
  title?: string
  coverImage?: string
  currentChapter?: string
  audiobookId?: string
}

// Message structure for BroadcastChannel
export interface AudioSyncMessage {
  type: AudioSyncMessageType
  payload?: Partial<AudioState> & { seekTime?: number }
  source: 'main' | 'popout'
  timestamp: number
}

interface UseAudioSyncOptions {
  // Whether this instance is the pop-out window
  isPopout?: boolean
  // Callback when state should be updated from remote
  onStateUpdate?: (state: Partial<AudioState>) => void
  // Callback when pop-out window status changes
  onPopoutStatusChange?: (isOpen: boolean) => void
}

interface UseAudioSyncReturn {
  // Send a message to other windows
  broadcast: (type: AudioSyncMessageType, payload?: AudioSyncMessage['payload']) => void
  // Whether the pop-out window is currently open
  isPopoutOpen: boolean
  // Open the pop-out player window
  openPopout: (state: AudioState) => Window | null
  // Close the pop-out player window
  closePopout: () => void
  // Request current state from other windows
  requestState: () => void
}

export function useAudioSync(options: UseAudioSyncOptions = {}): UseAudioSyncReturn {
  const { isPopout = false, onStateUpdate, onPopoutStatusChange } = options
  
  const channelRef = useRef<BroadcastChannel | null>(null)
  const popoutWindowRef = useRef<Window | null>(null)
  const [isPopoutOpen, setIsPopoutOpen] = useState(false)
  
  // Initialize BroadcastChannel
  useEffect(() => {
    // Check if BroadcastChannel is supported
    if (typeof BroadcastChannel === 'undefined') {
      console.warn('BroadcastChannel API not supported in this browser')
      return
    }
    
    channelRef.current = new BroadcastChannel(AUDIO_SYNC_CHANNEL)
    
    // Handle incoming messages
    channelRef.current.onmessage = (event: MessageEvent<AudioSyncMessage>) => {
      const message = event.data
      
      // Ignore messages from self
      if ((isPopout && message.source === 'popout') || 
          (!isPopout && message.source === 'main')) {
        return
      }
      
      switch (message.type) {
        case 'PLAY':
        case 'PAUSE':
        case 'SPEED_CHANGE':
        case 'TIME_UPDATE':
        case 'METADATA_UPDATE':
          onStateUpdate?.(message.payload || {})
          break
          
        case 'SEEK':
          if (message.payload?.seekTime !== undefined) {
            onStateUpdate?.({ currentTime: message.payload.seekTime })
          }
          break
          
        case 'POPOUT_OPENED':
          if (!isPopout) {
            setIsPopoutOpen(true)
            onPopoutStatusChange?.(true)
          }
          break
          
        case 'POPOUT_CLOSED':
          if (!isPopout) {
            setIsPopoutOpen(false)
            onPopoutStatusChange?.(false)
          }
          break
          
        case 'REQUEST_STATE':
          // Only main window responds with full state
          if (!isPopout && onStateUpdate) {
            // Main window should broadcast current state
            // This is handled in the component using this hook
          }
          break
          
        case 'STATE_RESPONSE':
          if (isPopout && message.payload) {
            onStateUpdate?.(message.payload)
          }
          break
      }
    }
    
    // If this is the pop-out window, notify main window
    if (isPopout) {
      channelRef.current.postMessage({
        type: 'POPOUT_OPENED',
        source: 'popout',
        timestamp: Date.now()
      } as AudioSyncMessage)
    }
    
    // Cleanup
    return () => {
      if (isPopout && channelRef.current) {
        channelRef.current.postMessage({
          type: 'POPOUT_CLOSED',
          source: 'popout',
          timestamp: Date.now()
        } as AudioSyncMessage)
      }
      channelRef.current?.close()
    }
  }, [isPopout, onStateUpdate, onPopoutStatusChange])
  
  // Monitor pop-out window close (for main window)
  useEffect(() => {
    if (isPopout || !popoutWindowRef.current) return
    
    const checkPopoutClosed = setInterval(() => {
      if (popoutWindowRef.current?.closed) {
        setIsPopoutOpen(false)
        onPopoutStatusChange?.(false)
        popoutWindowRef.current = null
        clearInterval(checkPopoutClosed)
      }
    }, 500)
    
    return () => clearInterval(checkPopoutClosed)
  }, [isPopout, isPopoutOpen, onPopoutStatusChange])
  
  // Broadcast a message to other windows
  const broadcast = useCallback((
    type: AudioSyncMessageType,
    payload?: AudioSyncMessage['payload']
  ) => {
    if (!channelRef.current) return
    
    const message: AudioSyncMessage = {
      type,
      payload,
      source: isPopout ? 'popout' : 'main',
      timestamp: Date.now()
    }
    
    channelRef.current.postMessage(message)
  }, [isPopout])
  
  // Open the pop-out player window
  const openPopout = useCallback((state: AudioState): Window | null => {
    if (isPopout) return null
    
    // Encode state in URL for initial load
    const stateParam = encodeURIComponent(JSON.stringify(state))
    const popoutUrl = `/player-popout?state=${stateParam}`
    
    // Calculate window position (right side of screen)
    const width = 400
    const height = 500
    const left = window.screenX + window.outerWidth - width - 50
    const top = window.screenY + 100
    
    const popout = window.open(
      popoutUrl,
      'audiobooker-popout',
      `width=${width},height=${height},left=${left},top=${top},resizable=yes,scrollbars=no`
    )
    
    if (popout) {
      popoutWindowRef.current = popout
      setIsPopoutOpen(true)
      onPopoutStatusChange?.(true)
      
      // Focus the pop-out window
      popout.focus()
    }
    
    return popout
  }, [isPopout, onPopoutStatusChange])
  
  // Close the pop-out window
  const closePopout = useCallback(() => {
    if (popoutWindowRef.current && !popoutWindowRef.current.closed) {
      popoutWindowRef.current.close()
    }
    popoutWindowRef.current = null
    setIsPopoutOpen(false)
    onPopoutStatusChange?.(false)
  }, [onPopoutStatusChange])
  
  // Request current state from other windows
  const requestState = useCallback(() => {
    broadcast('REQUEST_STATE')
  }, [broadcast])
  
  return {
    broadcast,
    isPopoutOpen,
    openPopout,
    closePopout,
    requestState
  }
}

export default useAudioSync
