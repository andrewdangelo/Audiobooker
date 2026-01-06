/**
 * PopoutPlayer Component
 * 
 * Minimal audio player UI designed for pop-out window.
 * Synchronizes playback state with the main window using BroadcastChannel.
 * 
 * Features:
 * - Compact, focused UI
 * - Play/Pause, Skip forward/backward
 * - Seek bar with time display
 * - Playback speed control
 * - Always-on-top appearance
 * 
 * @author Andrew D'Angelo
 * @version 1.0.0
 */

import { useState, useRef, useEffect, useCallback } from 'react'
import { Play, Pause, SkipForward, SkipBack, X } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Slider } from '@/components/ui/slider'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { useAudioSync, AudioState } from '@/hooks/useAudioSync'

interface PopoutPlayerProps {
  initialState?: AudioState
}

export default function PopoutPlayer({ initialState }: PopoutPlayerProps) {
  // Audio element reference
  const audioRef = useRef<HTMLAudioElement>(null)
  
  // Playback state
  const [isPlaying, setIsPlaying] = useState(initialState?.isPlaying || false)
  const [currentTime, setCurrentTime] = useState(initialState?.currentTime || 0)
  const [duration, setDuration] = useState(initialState?.duration || 0)
  const [playbackRate, setPlaybackRate] = useState(initialState?.playbackRate || 1.0)
  const [isSeeking, setIsSeeking] = useState(false)
  
  // Metadata
  const [audioUrl] = useState(initialState?.audioUrl)
  const [title] = useState(initialState?.title || 'Untitled Audiobook')
  const [coverImage] = useState(initialState?.coverImage)
  const [currentChapter] = useState(initialState?.currentChapter || '')
  
  // Flag to prevent echo when updating from broadcast
  const isRemoteUpdateRef = useRef(false)
  
  // Handle state updates from main window
  const handleStateUpdate = useCallback((state: Partial<AudioState>) => {
    isRemoteUpdateRef.current = true
    
    if (state.isPlaying !== undefined) {
      setIsPlaying(state.isPlaying)
      if (audioRef.current) {
        if (state.isPlaying) {
          audioRef.current.play().catch(console.error)
        } else {
          audioRef.current.pause()
        }
      }
    }
    
    if (state.currentTime !== undefined && audioRef.current) {
      audioRef.current.currentTime = state.currentTime
      setCurrentTime(state.currentTime)
    }
    
    if (state.playbackRate !== undefined && audioRef.current) {
      audioRef.current.playbackRate = state.playbackRate
      setPlaybackRate(state.playbackRate)
    }
    
    if (state.duration !== undefined) {
      setDuration(state.duration)
    }
    
    // Reset flag after a short delay
    setTimeout(() => {
      isRemoteUpdateRef.current = false
    }, 100)
  }, [])
  
  // Initialize audio sync hook
  const { broadcast } = useAudioSync({
    isPopout: true,
    onStateUpdate: handleStateUpdate
  })
  
  // Initialize audio element with initial state
  useEffect(() => {
    if (!audioRef.current || !initialState) return
    
    audioRef.current.currentTime = initialState.currentTime || 0
    audioRef.current.playbackRate = initialState.playbackRate || 1.0
    
    if (initialState.isPlaying) {
      audioRef.current.play().catch(console.error)
    }
  }, [initialState])
  
  // Toggle play/pause
  const togglePlayPause = () => {
    if (!audioRef.current) return
    
    const newIsPlaying = !isPlaying
    
    if (newIsPlaying) {
      audioRef.current.play().catch(console.error)
    } else {
      audioRef.current.pause()
    }
    
    setIsPlaying(newIsPlaying)
    broadcast(newIsPlaying ? 'PLAY' : 'PAUSE', { isPlaying: newIsPlaying })
  }
  
  // Skip forward
  const skipForward = (seconds: number = 30) => {
    if (!audioRef.current) return
    const newTime = Math.min(audioRef.current.currentTime + seconds, duration)
    audioRef.current.currentTime = newTime
    setCurrentTime(newTime)
    broadcast('SEEK', { seekTime: newTime })
  }
  
  // Skip backward
  const skipBackward = (seconds: number = 30) => {
    if (!audioRef.current) return
    const newTime = Math.max(audioRef.current.currentTime - seconds, 0)
    audioRef.current.currentTime = newTime
    setCurrentTime(newTime)
    broadcast('SEEK', { seekTime: newTime })
  }
  
  // Handle seek
  const handleSeek = (value: number[]) => {
    if (!audioRef.current) return
    const newTime = value[0]
    audioRef.current.currentTime = newTime
    setCurrentTime(newTime)
    broadcast('SEEK', { seekTime: newTime })
  }
  
  // Handle speed change
  const handleSpeedChange = (rate: number) => {
    if (!audioRef.current) return
    audioRef.current.playbackRate = rate
    setPlaybackRate(rate)
    broadcast('SPEED_CHANGE', { playbackRate: rate })
  }
  
  // Handle time update
  const handleTimeUpdate = () => {
    if (!audioRef.current || isSeeking || isRemoteUpdateRef.current) return
    setCurrentTime(audioRef.current.currentTime)
    
    // Broadcast time update periodically (every second)
    if (Math.floor(audioRef.current.currentTime) !== Math.floor(currentTime)) {
      broadcast('TIME_UPDATE', { 
        currentTime: audioRef.current.currentTime,
        isPlaying 
      })
    }
  }
  
  // Handle metadata loaded
  const handleLoadedMetadata = () => {
    if (!audioRef.current) return
    setDuration(audioRef.current.duration)
  }
  
  // Handle audio ended
  const handleEnded = () => {
    setIsPlaying(false)
    broadcast('PAUSE', { isPlaying: false })
  }
  
  // Format time
  const formatTime = (seconds: number): string => {
    if (isNaN(seconds)) return '00:00'
    
    const hrs = Math.floor(seconds / 3600)
    const mins = Math.floor((seconds % 3600) / 60)
    const secs = Math.floor(seconds % 60)
    
    if (hrs > 0) {
      return `${hrs}:${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`
    }
    return `${mins}:${secs.toString().padStart(2, '0')}`
  }
  
  // Get remaining time
  const getRemainingTime = (): string => {
    const remaining = duration - currentTime
    return formatTime(remaining)
  }
  
  // Close window
  const handleClose = () => {
    window.close()
  }
  
  const playbackSpeeds = [0.5, 0.75, 1.0, 1.25, 1.5, 1.75, 2.0]
  
  return (
    <div className="min-h-screen bg-background flex flex-col">
      {/* Hidden audio element */}
      <audio
        ref={audioRef}
        src={audioUrl}
        onTimeUpdate={handleTimeUpdate}
        onLoadedMetadata={handleLoadedMetadata}
        onEnded={handleEnded}
        preload="metadata"
      />
      
      {/* Header with close button */}
      <div className="flex items-center justify-between p-3 border-b bg-muted/50">
        <span className="text-sm font-medium text-muted-foreground">
          Pop-out Player
        </span>
        <Button
          variant="ghost"
          size="icon"
          onClick={handleClose}
          className="h-8 w-8"
          aria-label="Close pop-out player"
        >
          <X className="h-4 w-4" />
        </Button>
      </div>
      
      {/* Main content */}
      <div className="flex-1 p-4 flex flex-col">
        {/* Cover art */}
        <div className="flex justify-center mb-4">
          {coverImage ? (
            <img
              src={coverImage}
              alt={title}
              className="w-40 h-40 rounded-lg shadow-lg object-cover"
            />
          ) : (
            <div className="w-40 h-40 rounded-lg bg-gradient-to-br from-primary/80 to-primary flex items-center justify-center shadow-lg">
              <svg
                className="w-20 h-20 text-white"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M9 19V6l12-3v13M9 19c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zm12-3c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zM9 10l12-3"
                />
              </svg>
            </div>
          )}
        </div>
        
        {/* Title and chapter */}
        <div className="text-center mb-4">
          <h1 className="text-lg font-bold truncate px-2">{title}</h1>
          {currentChapter && (
            <p className="text-sm text-muted-foreground truncate px-2">
              {currentChapter}
            </p>
          )}
        </div>
        
        {/* Progress bar */}
        <div className="mb-4 px-2">
          <Slider
            value={[currentTime]}
            max={duration || 100}
            step={1}
            onValueChange={handleSeek}
            onPointerDown={() => setIsSeeking(true)}
            onPointerUp={() => setIsSeeking(false)}
            className="w-full mb-2 cursor-pointer"
          />
          <div className="flex justify-between text-xs text-muted-foreground">
            <span>{formatTime(currentTime)}</span>
            <span>−{getRemainingTime()}</span>
          </div>
        </div>
        
        {/* Main controls */}
        <div className="flex items-center justify-center gap-3 mb-4">
          {/* Skip backward */}
          <Button
            variant="ghost"
            size="icon"
            onClick={() => skipBackward(30)}
            className="h-10 w-10"
            aria-label="Skip back 30 seconds"
          >
            <div className="relative">
              <SkipBack className="h-5 w-5" />
              <span className="absolute inset-0 flex items-center justify-center text-[10px] font-bold">
                30
              </span>
            </div>
          </Button>
          
          {/* Play/Pause */}
          <Button
            size="icon"
            onClick={togglePlayPause}
            className="h-14 w-14 rounded-full bg-primary text-primary-foreground hover:bg-primary/90 shadow-lg"
            aria-label={isPlaying ? 'Pause' : 'Play'}
          >
            {isPlaying ? (
              <Pause className="h-7 w-7" fill="currentColor" />
            ) : (
              <Play className="h-7 w-7 ml-0.5" fill="currentColor" />
            )}
          </Button>
          
          {/* Skip forward */}
          <Button
            variant="ghost"
            size="icon"
            onClick={() => skipForward(30)}
            className="h-10 w-10"
            aria-label="Skip forward 30 seconds"
          >
            <div className="relative">
              <SkipForward className="h-5 w-5" />
              <span className="absolute inset-0 flex items-center justify-center text-[10px] font-bold">
                30
              </span>
            </div>
          </Button>
        </div>
        
        {/* Speed control */}
        <div className="flex justify-center">
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="outline" size="sm">
                <span className="font-semibold">{playbackRate}×</span>
                <span className="ml-1 text-xs text-muted-foreground">Speed</span>
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent className="bg-popover border">
              {playbackSpeeds.map((speed) => (
                <DropdownMenuItem
                  key={speed}
                  onClick={() => handleSpeedChange(speed)}
                  className={`cursor-pointer ${
                    playbackRate === speed ? 'bg-accent' : ''
                  }`}
                >
                  {speed}× {speed === 1.0 ? '(Normal)' : ''}
                </DropdownMenuItem>
              ))}
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </div>
      
      {/* Footer hint */}
      <div className="p-2 text-center border-t bg-muted/30">
        <p className="text-xs text-muted-foreground">
          Synced with main window
        </p>
      </div>
    </div>
  )
}
