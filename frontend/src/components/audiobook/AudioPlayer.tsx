/**
 * AudioPlayer Component
 * 
 * A comprehensive audio player for audiobook playback with features including:
 * - Play/Pause controls
 * - Skip forward/backward (30 seconds by default)
 * - Progress bar with seek functionality
 * - Playback speed control (0.5x - 2.0x)
 * - Chapter navigation (when integrated with API)
 * - Time display (current/total)
 * - Bookmark functionality (prepared for API integration)
 * - Pop-out player with cross-window synchronization
 * 
 * API Integration Points:
 * - Line 95-100: Fetch audio file URL from API
 * - Line 205-210: Save playback position to API
 * - Line 215-220: Fetch/Save bookmarks to API
 * - Line 225-230: Fetch chapter data from API
 * 
 * @author Audiobooker Team
 * @version 1.0.0
 */

import { useState, useRef, useCallback } from 'react'
import { Play, Pause, SkipForward, SkipBack, Bookmark, List, ExternalLink, X } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Slider } from '@/components/ui/slider'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { useAudioSync, AudioState } from '@/hooks/useAudioSync'

// Props interface for the AudioPlayer component
interface AudioPlayerProps {
  // Audiobook ID for API integration
  audiobookId?: string
  // Optional: Direct audio URL (for testing without API)
  audioUrl?: string
  // Audiobook title to display
  title?: string
  // Optional: Cover image URL
  coverImage?: string
  // Optional: Chapter name being played
  currentChapter?: string
}

/**
 * Main AudioPlayer Component
 * 
 * This component manages all audio playback state and provides
 * a rich user interface for controlling audiobook playback.
 */
export default function AudioPlayer({
  audiobookId, // Used for future API integration (see API Integration Points above)
  audioUrl,
  title = 'Untitled Audiobook',
  coverImage,
  currentChapter = 'Chapter 1'
}: AudioPlayerProps) {
  // ==================== State Management ====================
  
  // Audio element reference for programmatic control
  const audioRef = useRef<HTMLAudioElement>(null)
  
  // Playback state
  const [isPlaying, setIsPlaying] = useState(false)
  const [currentTime, setCurrentTime] = useState(0)
  const [duration, setDuration] = useState(0)
  const [playbackRate, setPlaybackRate] = useState(1.0)
  
  // UI state
  const [isSeeking, setIsSeeking] = useState(false)
  const [showChapters, setShowChapters] = useState(false)
  
  // Flag to prevent echo when updating from broadcast
  const isRemoteUpdateRef = useRef(false)
  
  // ==================== Pop-out Sync ====================
  
  // Handle state updates from pop-out window
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
  const { broadcast, isPopoutOpen, openPopout, closePopout } = useAudioSync({
    isPopout: false,
    onStateUpdate: handleStateUpdate
  })
  
  // Get current audio state for pop-out
  const getCurrentState = useCallback((): AudioState => ({
    isPlaying,
    currentTime,
    duration,
    playbackRate,
    audioUrl,
    title,
    coverImage,
    currentChapter,
    audiobookId
  }), [isPlaying, currentTime, duration, playbackRate, audioUrl, title, coverImage, currentChapter, audiobookId])
  
  // Handle opening pop-out player
  const handleOpenPopout = () => {
    openPopout(getCurrentState())
  }
  
  // ==================== API Integration Point #1 ====================
  /**
   * TODO: Replace with actual API call to fetch audio file
   * 
   * Example API call:
   * ```typescript
   * useEffect(() => {
   *   if (audiobookId) {
   *     fetch(`/api/v1/audiobooks/${audiobookId}`)
   *       .then(res => res.json())
   *       .then(data => {
   *         // Set audioUrl from API response
   *         if (audioRef.current) {
   *           audioRef.current.src = data.audioUrl
   *         }
   *       })
   *   }
   * }, [audiobookId])
   * ```
   */
  // Prevent unused variable warning - this will be used when API is integrated
  void audiobookId
  
  // ==================== Audio Control Functions ====================
  
  /**
   * Toggle play/pause state
   * Updates the audio element and component state accordingly
   */
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
  
  /**
   * Skip forward by specified seconds (default: 30)
   * @param seconds - Number of seconds to skip forward
   */
  const skipForward = (seconds: number = 30) => {
    if (!audioRef.current) return
    const newTime = Math.min(audioRef.current.currentTime + seconds, duration)
    audioRef.current.currentTime = newTime
    setCurrentTime(newTime)
    broadcast('SEEK', { seekTime: newTime })
  }
  
  /**
   * Skip backward by specified seconds (default: 30)
   * @param seconds - Number of seconds to skip backward
   */
  const skipBackward = (seconds: number = 30) => {
    if (!audioRef.current) return
    const newTime = Math.max(audioRef.current.currentTime - seconds, 0)
    audioRef.current.currentTime = newTime
    setCurrentTime(newTime)
    broadcast('SEEK', { seekTime: newTime })
  }
  
  /**
   * Handle playback speed change
   * @param rate - New playback rate (0.5x to 2.0x)
   */
  const handleSpeedChange = (rate: number) => {
    if (!audioRef.current) return
    audioRef.current.playbackRate = rate
    setPlaybackRate(rate)
    broadcast('SPEED_CHANGE', { playbackRate: rate })
  }
  
  /**
   * Handle seek/scrub through audio
   * @param value - Array with single value representing new time
   */
  const handleSeek = (value: number[]) => {
    if (!audioRef.current) return
    const newTime = value[0]
    audioRef.current.currentTime = newTime
    setCurrentTime(newTime)
    broadcast('SEEK', { seekTime: newTime })
  }
  
  // ==================== Audio Event Handlers ====================
  
  /**
   * Update current time as audio plays
   * Also saves progress to API periodically
   */
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
    
    // ==================== API Integration Point #2 ====================
    /**
     * TODO: Save playback position to API every 30 seconds
     * 
     * Example API call:
     * ```typescript
     * if (Math.floor(audioRef.current.currentTime) % 30 === 0) {
     *   fetch(`/api/v1/audiobooks/${audiobookId}/progress`, {
     *     method: 'PUT',
     *     body: JSON.stringify({ 
     *       position: audioRef.current.currentTime 
     *     })
     *   })
     * }
     * ```
     */
  }
  
  /**
   * Set duration when metadata is loaded
   */
  const handleLoadedMetadata = () => {
    if (!audioRef.current) return
    setDuration(audioRef.current.duration)
  }
  
  /**
   * Handle audio ended event
   */
  const handleEnded = () => {
    setIsPlaying(false)
    // TODO: API call to mark chapter/audiobook as completed
  }
  
  // ==================== Bookmark Functionality ====================
  
  /**
   * Add bookmark at current position
   * 
   * ==================== API Integration Point #3 ====================
   * TODO: Save bookmark to API
   * 
   * Example API call:
   * ```typescript
   * const addBookmark = async () => {
   *   await fetch(`/api/v1/audiobooks/${audiobookId}/bookmarks`, {
   *     method: 'POST',
   *     body: JSON.stringify({
   *       position: currentTime,
   *       chapterName: currentChapter,
   *       note: '' // Optional user note
   *     })
   *   })
   * }
   * ```
   */
  const addBookmark = () => {
    console.log('Bookmark added at:', formatTime(currentTime))
    // TODO: Implement API call to save bookmark
    alert(`Bookmark added at ${formatTime(currentTime)}`)
  }
  
  // ==================== Chapter Navigation ====================
  
  /**
   * ==================== API Integration Point #4 ====================
   * TODO: Fetch chapters from API and implement navigation
   * 
   * Example API call:
   * ```typescript
   * useEffect(() => {
   *   if (audiobookId) {
   *     fetch(`/api/v1/audiobooks/${audiobookId}/chapters`)
   *       .then(res => res.json())
   *       .then(chapters => {
   *         // Set chapters state
   *         // Enable chapter navigation
   *       })
   *   }
   * }, [audiobookId])
   * ```
   */
  
  // ==================== Utility Functions ====================
  
  /**
   * Format time in seconds to MM:SS or HH:MM:SS format
   * @param seconds - Time in seconds
   * @returns Formatted time string
   */
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
  
  /**
   * Calculate remaining time
   * @returns Formatted remaining time string
   */
  const getRemainingTime = (): string => {
    const remaining = duration - currentTime
    return formatTime(remaining)
  }
  
  // Available playback speeds
  const playbackSpeeds = [0.5, 0.75, 1.0, 1.25, 1.5, 1.75, 2.0]
  
  // ==================== Render ====================
  
  return (
    <div className="w-full bg-card border rounded-lg shadow-lg overflow-hidden">
      {/* Hidden audio element - controlled programmatically */}
      <audio
        ref={audioRef}
        src={audioUrl}
        onTimeUpdate={handleTimeUpdate}
        onLoadedMetadata={handleLoadedMetadata}
        onEnded={handleEnded}
        preload="metadata"
      />
      
      {/* Main Player Container */}
      <div className="p-6">
        {/* Cover Art and Info Section */}
        <div className="flex items-center gap-6 mb-6">
          {/* Album/Book Cover */}
          <div className="flex-shrink-0">
            {coverImage ? (
              <img
                src={coverImage}
                alt={title}
                className="w-32 h-32 rounded-lg shadow-lg object-cover"
              />
            ) : (
              <div className="w-32 h-32 rounded-lg bg-gradient-to-br from-primary/80 to-primary flex items-center justify-center shadow-lg">
                <svg
                  className="w-16 h-16 text-white"
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
          
          {/* Title and Chapter Info */}
          <div className="flex-1 min-w-0">
            <h2 className="text-2xl font-bold truncate mb-1">
              {title}
            </h2>
            <p className="text-muted-foreground text-sm truncate">
              {currentChapter}
            </p>
          </div>
        </div>
        
        {/* Progress Bar Section */}
        <div className="mb-4">
          {/* Progress Slider */}
          <Slider
            value={[currentTime]}
            max={duration || 100}
            step={1}
            onValueChange={handleSeek}
            onPointerDown={() => setIsSeeking(true)}
            onPointerUp={() => setIsSeeking(false)}
            className="w-full mb-2 cursor-pointer"
          />
          
          {/* Time Display */}
          <div className="flex justify-between text-sm text-muted-foreground">
            <span>{formatTime(currentTime)}</span>
            <span>−{getRemainingTime()}</span>
          </div>
        </div>
        
        {/* Main Controls Section */}
        <div className="flex items-center justify-center gap-4 mb-4">
          {/* Skip Backward 30s */}
          <Button
            variant="ghost"
            size="icon"
            onClick={() => skipBackward(30)}
            className="hover:bg-accent transition-colors"
            aria-label="Skip back 30 seconds"
          >
            <div className="relative">
              <SkipBack className="h-6 w-6" />
              <span className="absolute inset-0 flex items-center justify-center text-xs font-bold">
                30
              </span>
            </div>
          </Button>
          
          {/* Play/Pause Button */}
          <Button
            size="icon"
            onClick={togglePlayPause}
            className="h-16 w-16 rounded-full bg-primary text-primary-foreground hover:bg-primary/90 transition-all transform hover:scale-105 shadow-lg"
            aria-label={isPlaying ? 'Pause' : 'Play'}
          >
            {isPlaying ? (
              <Pause className="h-8 w-8" fill="currentColor" />
            ) : (
              <Play className="h-8 w-8 ml-1" fill="currentColor" />
            )}
          </Button>
          
          {/* Skip Forward 30s */}
          <Button
            variant="ghost"
            size="icon"
            onClick={() => skipForward(30)}
            className="hover:bg-accent transition-colors"
            aria-label="Skip forward 30 seconds"
          >
            <div className="relative">
              <SkipForward className="h-6 w-6" />
              <span className="absolute inset-0 flex items-center justify-center text-xs font-bold">
                30
              </span>
            </div>
          </Button>
        </div>
        
        {/* Secondary Controls Section */}
        <div className="flex items-center justify-between">
          {/* Playback Speed Control */}
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button
                variant="ghost"
                size="sm"
                className="hover:bg-accent"
              >
                <span className="font-semibold">{playbackRate}×</span>
                <span className="ml-1 text-xs text-muted-foreground">Speed</span>
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent className="bg-popover border">
              {playbackSpeeds.map((speed) => (
                <DropdownMenuItem
                  key={speed}
                  onClick={() => handleSpeedChange(speed)}
                  className={`hover:bg-accent cursor-pointer ${
                    playbackRate === speed ? 'bg-accent' : ''
                  }`}
                >
                  {speed}× {speed === 1.0 ? '(Normal)' : ''}
                </DropdownMenuItem>
              ))}
            </DropdownMenuContent>
          </DropdownMenu>
          
          {/* Center controls group */}
          <div className="flex items-center gap-1">
            {/* Chapters Button */}
            <Button
              variant="ghost"
              size="icon"
              onClick={() => setShowChapters(!showChapters)}
              className="hover:bg-accent"
              aria-label="View chapters"
            >
              <List className="h-5 w-5" />
            </Button>
            
            {/* Add Bookmark Button */}
            <Button
              variant="ghost"
              size="icon"
              onClick={addBookmark}
              className="hover:bg-accent"
              aria-label="Add bookmark"
            >
              <Bookmark className="h-5 w-5" />
            </Button>
          </div>
          
          {/* Pop-out Button */}
          {isPopoutOpen ? (
            <Button
              variant="ghost"
              size="sm"
              onClick={closePopout}
              className="hover:bg-accent text-primary"
              aria-label="Close pop-out player"
            >
              <X className="h-4 w-4 mr-1" />
              <span className="text-xs">Close Pop-out</span>
            </Button>
          ) : (
            <Button
              variant="ghost"
              size="sm"
              onClick={handleOpenPopout}
              className="hover:bg-accent"
              aria-label="Open pop-out player"
            >
              <ExternalLink className="h-4 w-4 mr-1" />
              <span className="text-xs">Pop-out</span>
            </Button>
          )}
        </div>
        
        {/* Pop-out status indicator */}
        {isPopoutOpen && (
          <div className="mt-3 p-2 bg-primary/10 rounded-lg border border-primary/20 text-center">
            <p className="text-xs text-primary font-medium">
              🔗 Synced with pop-out player
            </p>
          </div>
        )}
        
        {/* Chapters Panel (conditionally shown) */}
        {showChapters && (
          <div className="mt-4 p-4 bg-muted rounded-lg border">
            <h3 className="font-semibold mb-2">Chapters</h3>
            <p className="text-muted-foreground text-sm">
              Chapter navigation will be available when integrated with the API.
            </p>
            {/* 
              TODO: Map through chapters from API
              Example:
              {chapters.map(chapter => (
                <button onClick={() => seekToChapter(chapter.startTime)}>
                  {chapter.name}
                </button>
              ))}
            */}
          </div>
        )}
      </div>
    </div>
  )
}
