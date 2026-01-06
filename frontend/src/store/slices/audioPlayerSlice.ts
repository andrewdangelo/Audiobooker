/**
 * Audio Player Slice
 * 
 * Manages global audio player state including playback, progress, and queue.
 * This state is synchronized across windows using BroadcastChannel.
 * Persisted to remember last played audiobook and position.
 * 
 * @author Andrew D'Angelo
 * 
 * HOW TO USE:
 * - Import actions: import { play, pause, seek, setCurrentTrack } from '@/store'
 * - Import selectors: import { selectIsPlaying, selectCurrentTrack } from '@/store'
 */

import { createSlice, PayloadAction } from '@reduxjs/toolkit'
import type { RootState } from '../index'

// Types
export interface AudioTrack {
  id: string
  title: string
  author?: string
  audioUrl: string
  coverImage?: string
  duration: number
  chapters?: AudioChapter[]
}

export interface AudioChapter {
  id: string
  title: string
  startTime: number
  duration: number
}

export interface AudioPlayerState {
  // Current track info
  currentTrack: AudioTrack | null
  
  // Playback state
  isPlaying: boolean
  currentTime: number
  duration: number
  playbackRate: number
  volume: number
  isMuted: boolean
  
  // Current chapter
  currentChapterIndex: number
  
  // Queue
  queue: AudioTrack[]
  queueIndex: number
  
  // Repeat/Shuffle
  repeatMode: 'off' | 'one' | 'all'
  shuffleEnabled: boolean
  
  // Pop-out player state
  isPopoutOpen: boolean
  
  // Loading state
  isBuffering: boolean
}

// Initial state
const initialState: AudioPlayerState = {
  currentTrack: null,
  isPlaying: false,
  currentTime: 0,
  duration: 0,
  playbackRate: 1,
  volume: 1,
  isMuted: false,
  currentChapterIndex: 0,
  queue: [],
  queueIndex: 0,
  repeatMode: 'off',
  shuffleEnabled: false,
  isPopoutOpen: false,
  isBuffering: false,
}

// Slice
const audioPlayerSlice = createSlice({
  name: 'audioPlayer',
  initialState,
  reducers: {
    // Set the current track to play
    setCurrentTrack: (state, action: PayloadAction<AudioTrack>) => {
      state.currentTrack = action.payload
      state.duration = action.payload.duration
      state.currentTime = 0
      state.currentChapterIndex = 0
    },
    
    // Play/Pause controls
    play: (state) => {
      state.isPlaying = true
    },
    
    pause: (state) => {
      state.isPlaying = false
    },
    
    togglePlayPause: (state) => {
      state.isPlaying = !state.isPlaying
    },
    
    // Seek to specific time
    seek: (state, action: PayloadAction<number>) => {
      state.currentTime = Math.max(0, Math.min(action.payload, state.duration))
      
      // Update current chapter based on seek time
      if (state.currentTrack?.chapters) {
        const chapterIndex = state.currentTrack.chapters.findIndex(
          (ch, i, arr) => {
            const nextChapter = arr[i + 1]
            return action.payload >= ch.startTime && 
              (!nextChapter || action.payload < nextChapter.startTime)
          }
        )
        if (chapterIndex !== -1) {
          state.currentChapterIndex = chapterIndex
        }
      }
    },
    
    // Update current time (called frequently during playback)
    updateCurrentTime: (state, action: PayloadAction<number>) => {
      state.currentTime = action.payload
    },
    
    // Set playback speed
    setPlaybackRate: (state, action: PayloadAction<number>) => {
      state.playbackRate = action.payload
    },
    
    // Volume controls
    setVolume: (state, action: PayloadAction<number>) => {
      state.volume = Math.max(0, Math.min(1, action.payload))
      if (state.volume > 0) {
        state.isMuted = false
      }
    },
    
    toggleMute: (state) => {
      state.isMuted = !state.isMuted
    },
    
    // Chapter navigation
    setChapter: (state, action: PayloadAction<number>) => {
      if (state.currentTrack?.chapters && action.payload >= 0 && 
          action.payload < state.currentTrack.chapters.length) {
        state.currentChapterIndex = action.payload
        state.currentTime = state.currentTrack.chapters[action.payload].startTime
      }
    },
    
    nextChapter: (state) => {
      if (state.currentTrack?.chapters && 
          state.currentChapterIndex < state.currentTrack.chapters.length - 1) {
        state.currentChapterIndex += 1
        state.currentTime = state.currentTrack.chapters[state.currentChapterIndex].startTime
      }
    },
    
    previousChapter: (state) => {
      if (state.currentTrack?.chapters && state.currentChapterIndex > 0) {
        state.currentChapterIndex -= 1
        state.currentTime = state.currentTrack.chapters[state.currentChapterIndex].startTime
      }
    },
    
    // Queue management
    setQueue: (state, action: PayloadAction<AudioTrack[]>) => {
      state.queue = action.payload
      state.queueIndex = 0
    },
    
    addToQueue: (state, action: PayloadAction<AudioTrack>) => {
      state.queue.push(action.payload)
    },
    
    removeFromQueue: (state, action: PayloadAction<number>) => {
      state.queue.splice(action.payload, 1)
      if (state.queueIndex >= state.queue.length) {
        state.queueIndex = Math.max(0, state.queue.length - 1)
      }
    },
    
    clearQueue: (state) => {
      state.queue = []
      state.queueIndex = 0
    },
    
    // Play next/previous in queue
    playNext: (state) => {
      if (state.queueIndex < state.queue.length - 1) {
        state.queueIndex += 1
        state.currentTrack = state.queue[state.queueIndex]
        state.currentTime = 0
        state.currentChapterIndex = 0
      } else if (state.repeatMode === 'all') {
        state.queueIndex = 0
        state.currentTrack = state.queue[0]
        state.currentTime = 0
        state.currentChapterIndex = 0
      }
    },
    
    playPrevious: (state) => {
      // If more than 3 seconds into track, restart it
      if (state.currentTime > 3) {
        state.currentTime = 0
        state.currentChapterIndex = 0
      } else if (state.queueIndex > 0) {
        state.queueIndex -= 1
        state.currentTrack = state.queue[state.queueIndex]
        state.currentTime = 0
        state.currentChapterIndex = 0
      }
    },
    
    // Repeat/Shuffle
    setRepeatMode: (state, action: PayloadAction<'off' | 'one' | 'all'>) => {
      state.repeatMode = action.payload
    },
    
    toggleShuffle: (state) => {
      state.shuffleEnabled = !state.shuffleEnabled
    },
    
    // Pop-out player state
    setPopoutOpen: (state, action: PayloadAction<boolean>) => {
      state.isPopoutOpen = action.payload
    },
    
    // Buffering state
    setBuffering: (state, action: PayloadAction<boolean>) => {
      state.isBuffering = action.payload
    },
    
    // Reset player
    resetPlayer: (state) => {
      return { ...initialState, volume: state.volume, playbackRate: state.playbackRate }
    },
  },
})

// Export actions
export const {
  setCurrentTrack,
  play,
  pause,
  togglePlayPause,
  seek,
  updateCurrentTime,
  setPlaybackRate,
  setVolume,
  toggleMute,
  setChapter,
  nextChapter,
  previousChapter,
  setQueue,
  addToQueue,
  removeFromQueue,
  clearQueue,
  playNext,
  playPrevious,
  setRepeatMode,
  toggleShuffle,
  setPopoutOpen,
  setBuffering,
  resetPlayer,
} = audioPlayerSlice.actions

// Selectors
export const selectCurrentTrack = (state: RootState) => state.audioPlayer.currentTrack
export const selectIsPlaying = (state: RootState) => state.audioPlayer.isPlaying
export const selectCurrentTime = (state: RootState) => state.audioPlayer.currentTime
export const selectDuration = (state: RootState) => state.audioPlayer.duration
export const selectPlaybackRate = (state: RootState) => state.audioPlayer.playbackRate
export const selectVolume = (state: RootState) => state.audioPlayer.volume
export const selectIsMuted = (state: RootState) => state.audioPlayer.isMuted
export const selectCurrentChapterIndex = (state: RootState) => state.audioPlayer.currentChapterIndex
export const selectQueue = (state: RootState) => state.audioPlayer.queue
export const selectRepeatMode = (state: RootState) => state.audioPlayer.repeatMode
export const selectShuffleEnabled = (state: RootState) => state.audioPlayer.shuffleEnabled
export const selectIsPopoutOpen = (state: RootState) => state.audioPlayer.isPopoutOpen
export const selectIsBuffering = (state: RootState) => state.audioPlayer.isBuffering

// Computed selectors
export const selectCurrentChapter = (state: RootState) => {
  const track = state.audioPlayer.currentTrack
  const index = state.audioPlayer.currentChapterIndex
  return track?.chapters?.[index] || null
}

export const selectProgress = (state: RootState) => {
  const { currentTime, duration } = state.audioPlayer
  return duration > 0 ? (currentTime / duration) * 100 : 0
}

export default audioPlayerSlice.reducer
