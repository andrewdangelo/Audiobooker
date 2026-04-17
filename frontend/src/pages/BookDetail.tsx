/**
 * BookDetail Page
 *
 * Displays detailed information about an audiobook from the user's library.
 * Features: live progress sync from popout player, current-chapter detection,
 * per-chapter progress bars, full metadata, and chapter-level play controls.
 */

import { useEffect, useState, useCallback } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  Play, Pause, Clock, BookOpen, ArrowLeft, Headphones,
  CheckCircle2, Radio, Calendar, User, Hash, Tag,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { useAudioSync, AudioState } from '@/hooks/useAudioSync'
import {
  useAppDispatch,
  useAppSelector,
  fetchAudiobookById,
  selectAudiobookById,
  selectAudiobooksLoading,
} from '@/store'
import type { AudiobookChapter } from '@/store/slices/audiobooksSlice'
import ConversionWorkflow from '@/components/audiobook/ConversionWorkflow'

// ─── Helpers ────────────────────────────────────────────────────────────────

function formatDuration(seconds: number): string {
  if (!seconds || seconds <= 0) return '0 min'
  const h = Math.floor(seconds / 3600)
  const m = Math.floor((seconds % 3600) / 60)
  const s = Math.floor(seconds % 60)
  if (h > 0) return `${h} hr ${m} min`
  if (m > 0) return `${m} min`
  return `${s} sec`
}

function formatTime(seconds: number): string {
  const h = Math.floor(seconds / 3600)
  const m = Math.floor((seconds % 3600) / 60)
  const s = Math.floor(seconds % 60)
  if (h > 0) return `${h}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`
  return `${m}:${String(s).padStart(2, '0')}`
}

function relativeTime(iso?: string): string | null {
  if (!iso) return null
  const diff = Date.now() - new Date(iso).getTime()
  const mins = Math.floor(diff / 60_000)
  if (mins < 2) return 'just now'
  if (mins < 60) return `${mins} minutes ago`
  const hrs = Math.floor(mins / 60)
  if (hrs < 24) return `${hrs} hour${hrs === 1 ? '' : 's'} ago`
  const days = Math.floor(hrs / 24)
  if (days < 7) return `${days} day${days === 1 ? '' : 's'} ago`
  const weeks = Math.floor(days / 7)
  if (weeks < 5) return `${weeks} week${weeks === 1 ? '' : 's'} ago`
  return new Date(iso).toLocaleDateString()
}

/** Returns the index of the chapter that's currently playing given currentTime. */
function getChapterIndex(chapters: AudiobookChapter[], currentTime: number): number {
  let idx = 0
  for (let i = 0; i < chapters.length; i++) {
    if (chapters[i].startTime <= currentTime) idx = i
    else break
  }
  return idx
}

/** 0-100 progress within a single chapter. */
function chapterProgress(chapter: AudiobookChapter, currentTime: number, totalDuration: number): number {
  const end = chapter.startTime + (chapter.duration || (totalDuration - chapter.startTime))
  if (currentTime <= chapter.startTime) return 0
  if (currentTime >= end) return 100
  return Math.round(((currentTime - chapter.startTime) / (end - chapter.startTime)) * 100)
}

// ─── Component ──────────────────────────────────────────────────────────────

export default function BookDetail() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const dispatch = useAppDispatch()

  const book = useAppSelector((state) => selectAudiobookById(state, id ?? ''))
  const loading = useAppSelector(selectAudiobooksLoading)

  // Live playback state synced from the pop-out player via BroadcastChannel
  const [liveState, setLiveState] = useState<Partial<AudioState> | null>(null)
  const [isPopoutPlaying, setIsPopoutPlaying] = useState(false)

  const { broadcast, isPopoutOpen, openPopout, requestState } = useAudioSync({
    onStateUpdate: useCallback((state: Partial<AudioState>) => {
      // Only track live state if it's for this book
      if (!state.audiobookId || state.audiobookId === id) {
        setLiveState((prev) => ({ ...prev, ...state }))
        if (typeof state.isPlaying === 'boolean') setIsPopoutPlaying(state.isPlaying)
      }
    }, [id]),
  })

  useEffect(() => {
    if (id) dispatch(fetchAudiobookById(id))
  }, [id, dispatch])

  // When popout opens or page loads, ask for current state
  useEffect(() => {
    if (isPopoutOpen) requestState()
  }, [isPopoutOpen, requestState])

  if (loading && !book) {
    return (
      <div className="container mx-auto px-4 py-16 text-center text-muted-foreground">
        <div className="animate-pulse space-y-4">
          <div className="h-8 w-48 bg-muted rounded mx-auto" />
          <div className="h-4 w-64 bg-muted rounded mx-auto" />
        </div>
      </div>
    )
  }

  if (!book) {
    return (
      <div className="container mx-auto px-4 py-16 text-center">
        <h1 className="text-2xl font-bold mb-4">Book Not Found</h1>
        <p className="text-muted-foreground mb-6">
          This audiobook doesn't exist in your library or hasn't loaded yet.
        </p>
        <Button onClick={() => navigate('/library')}>
          <ArrowLeft className="h-4 w-4 mr-2" />
          Back to Library
        </Button>
      </div>
    )
  }

  if (book.conversion && book.status !== 'completed') {
    return <ConversionWorkflow book={book} />
  }

  const chapters = book.chapters ?? []
  const storedProgress = book.progress ?? 0

  // Prefer live position from popout; fall back to stored progress percentage
  const currentTime: number =
    (liveState?.audiobookId === id && typeof liveState?.currentTime === 'number')
      ? liveState.currentTime
      : (storedProgress / 100) * book.duration

  const progressPct = book.duration > 0 ? Math.min(100, (currentTime / book.duration) * 100) : storedProgress
  const timeRemaining = Math.max(0, book.duration - currentTime)

  const currentChapterIdx = chapters.length > 0 ? getChapterIndex(chapters, currentTime) : -1
  const currentChapter = currentChapterIdx >= 0 ? chapters[currentChapterIdx] : null

  const hasStarted = progressPct > 0.1

  function buildState(chapterStartTime?: number, chapterTitle?: string): AudioState {
    const jumpTo = chapterStartTime ?? (hasStarted ? currentTime : 0)
    const chTitle = chapterTitle ?? currentChapter?.title ?? (chapters[0]?.title ?? 'Chapter 1')
    return {
      isPlaying: true,
      currentTime: jumpTo,
      duration: book!.duration,
      playbackRate: 1.0,
      audioUrl: book!.audioUrl ?? '',
      title: book!.title,
      coverImage: book!.coverImage,
      currentChapter: chTitle,
      audiobookId: book!.id,
    }
  }

  const handlePlay = () => {
    if (isPopoutOpen) {
      // Toggle play/pause if popout already open for this book
      if (liveState?.audiobookId === id) {
        broadcast(isPopoutPlaying ? 'PAUSE' : 'PLAY')
        return
      }
    }
    openPopout(buildState())
  }

  const handlePlayChapter = (chapter: AudiobookChapter) => {
    if (isPopoutOpen) {
      broadcast('SEEK', { seekTime: chapter.startTime, currentChapter: chapter.title })
      broadcast('PLAY')
    } else {
      openPopout(buildState(chapter.startTime, chapter.title))
    }
  }

  // ── Render ──────────────────────────────────────────────────────────────

  return (
    <div className="min-h-screen">
      {/* Top bar */}
      <div className="sticky top-0 z-10 bg-background/80 backdrop-blur border-b">
        <div className="container mx-auto px-4 h-14 flex items-center gap-4">
          <Button variant="ghost" size="sm" onClick={() => navigate('/library')} className="-ml-2">
            <ArrowLeft className="h-4 w-4 mr-2" />
            Library
          </Button>
          {hasStarted && (
            <div className="flex-1 flex items-center gap-3 max-w-md">
              <div className="flex-1 h-1.5 bg-muted rounded-full overflow-hidden">
                <div
                  className="h-full bg-primary rounded-full transition-all duration-500"
                  style={{ width: `${progressPct}%` }}
                />
              </div>
              <span className="text-xs text-muted-foreground whitespace-nowrap">
                {Math.round(progressPct)}%
              </span>
            </div>
          )}
          {isPopoutOpen && (
            <Badge variant="secondary" className="gap-1.5 animate-pulse text-xs">
              <Radio className="h-3 w-3" />
              {isPopoutPlaying ? 'Playing' : 'Paused'}
            </Badge>
          )}
        </div>
      </div>

      <div className="container mx-auto px-4 py-8">
        <div className="grid lg:grid-cols-[280px_1fr] gap-10">

          {/* ── Left sidebar ── */}
          <div className="flex flex-col items-center lg:items-stretch gap-5">

            {/* Cover */}
            <div className="w-full max-w-[260px] mx-auto aspect-[3/4] rounded-2xl overflow-hidden shadow-2xl bg-gradient-to-br from-primary/20 to-primary/40">
              {book.coverImage ? (
                <img src={book.coverImage} alt={book.title} className="w-full h-full object-cover" />
              ) : (
                <div className="w-full h-full flex items-center justify-center">
                  <BookOpen className="w-20 h-20 text-primary/40" />
                </div>
              )}
            </div>

            {/* CTA button */}
            <Button
              size="lg"
              onClick={handlePlay}
              className="w-full max-w-[260px] mx-auto h-12 text-base font-semibold shadow-lg"
            >
              {isPopoutOpen && liveState?.audiobookId === id
                ? isPopoutPlaying
                  ? <><Pause className="h-5 w-5 mr-2" fill="currentColor" />Pause</>
                  : <><Play className="h-5 w-5 mr-2" fill="currentColor" />Resume</>
                : hasStarted
                  ? <><Play className="h-5 w-5 mr-2" fill="currentColor" />Continue Listening</>
                  : <><Play className="h-5 w-5 mr-2" fill="currentColor" />Play Audiobook</>
              }
            </Button>

            {/* Overall progress */}
            {hasStarted && (
              <div className="w-full max-w-[260px] mx-auto space-y-1.5">
                <div className="flex justify-between text-xs text-muted-foreground">
                  <span>{Math.round(progressPct)}% complete</span>
                  <span>{formatDuration(timeRemaining)} left</span>
                </div>
                <div className="h-2 bg-muted rounded-full overflow-hidden">
                  <div
                    className="h-full bg-primary rounded-full transition-all duration-500"
                    style={{ width: `${progressPct}%` }}
                  />
                </div>
                {currentChapter && (
                  <p className="text-xs text-muted-foreground text-center pt-0.5 truncate">
                    Currently on: <span className="font-medium text-foreground">{currentChapter.title}</span>
                  </p>
                )}
              </div>
            )}

            {/* Metadata pills */}
            <div className="w-full max-w-[260px] mx-auto space-y-2 text-sm">
              <MetaRow icon={<Clock className="h-4 w-4" />} label="Duration" value={formatDuration(book.duration)} />
              {book.narrator && (
                <MetaRow icon={<Headphones className="h-4 w-4" />} label="Narrator" value={book.narrator} />
              )}
              {book.author && (
                <MetaRow icon={<User className="h-4 w-4" />} label="Author" value={book.author} />
              )}
              {book.genre && (
                <MetaRow icon={<Tag className="h-4 w-4" />} label="Genre" value={book.genre} />
              )}
              {book.publishedYear && (
                <MetaRow icon={<Calendar className="h-4 w-4" />} label="Published" value={String(book.publishedYear)} />
              )}
              {chapters.length > 0 && (
                <MetaRow icon={<Hash className="h-4 w-4" />} label="Chapters" value={String(chapters.length)} />
              )}
              {book.lastPlayedAt && (
                <MetaRow icon={<Radio className="h-4 w-4" />} label="Last played" value={relativeTime(book.lastPlayedAt) ?? ''} />
              )}
            </div>
          </div>

          {/* ── Right main ── */}
          <div className="min-w-0">

            {/* Title / author */}
            <div className="mb-6">
              {book.genre && (
                <Badge variant="secondary" className="mb-3">{book.genre}</Badge>
              )}
              <h1 className="text-3xl lg:text-4xl font-bold leading-tight mb-1">{book.title}</h1>
              <p className="text-lg text-muted-foreground">by {book.author}</p>
            </div>

            {/* Description */}
            {book.description && (
              <div className="mb-8">
                <h2 className="text-lg font-semibold mb-2">About this book</h2>
                <p className="text-muted-foreground leading-relaxed">{book.description}</p>
              </div>
            )}

            {/* Chapters */}
            {chapters.length > 0 && (
              <div>
                <h2 className="text-lg font-semibold mb-3">
                  Chapters
                  {currentChapter && (
                    <span className="ml-2 text-sm font-normal text-muted-foreground">
                      — on {currentChapter.title}
                    </span>
                  )}
                </h2>

                <div className="space-y-1">
                  {chapters.map((chapter, index) => {
                    const isCurrent = index === currentChapterIdx
                    const chPct = chapterProgress(chapter, currentTime, book.duration)
                    const isCompleted = chPct >= 100
                    const isStarted = chPct > 0 && !isCompleted

                    return (
                      <div
                        key={chapter.id || index}
                        onClick={() => handlePlayChapter(chapter)}
                        className={[
                          'flex items-center gap-3 px-4 py-3 rounded-xl cursor-pointer transition-all group',
                          isCurrent
                            ? 'bg-primary/10 ring-1 ring-primary/30'
                            : 'hover:bg-muted/60',
                        ].join(' ')}
                      >
                        {/* Status icon / number */}
                        <div className="w-8 h-8 flex items-center justify-center flex-shrink-0">
                          {isCompleted ? (
                            <CheckCircle2 className="h-5 w-5 text-primary" />
                          ) : isCurrent && isPopoutPlaying ? (
                            <span className="flex gap-0.5 items-end h-5">
                              {[1, 2, 3].map((i) => (
                                <span
                                  key={i}
                                  className="w-1 bg-primary rounded-full animate-bounce"
                                  style={{ height: `${8 + i * 4}px`, animationDelay: `${i * 0.15}s` }}
                                />
                              ))}
                            </span>
                          ) : (
                            <span className={[
                              'text-sm font-semibold group-hover:hidden',
                              isCurrent ? 'text-primary' : 'text-muted-foreground',
                            ].join(' ')}>
                              {(index + 1).toString().padStart(2, '0')}
                            </span>
                          )}
                          {!isCompleted && !(isCurrent && isPopoutPlaying) && (
                            <Play
                              className="h-4 w-4 text-primary hidden group-hover:block flex-shrink-0"
                              fill="currentColor"
                            />
                          )}
                        </div>

                        {/* Title + progress bar */}
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 mb-0.5">
                            <p className={[
                              'font-medium truncate',
                              isCurrent ? 'text-primary' : '',
                            ].join(' ')}>
                              {chapter.title}
                            </p>
                            {isCurrent && isPopoutOpen && (
                              <Badge variant="default" className="text-[10px] h-4 px-1.5 shrink-0">
                                {isPopoutPlaying ? 'NOW PLAYING' : 'PAUSED'}
                              </Badge>
                            )}
                          </div>
                          <div className="flex items-center gap-2">
                            <span className="text-xs text-muted-foreground">
                              {formatDuration(chapter.duration)}
                            </span>
                            {isStarted && (
                              <span className="text-xs text-primary font-medium">
                                {chPct}% in
                              </span>
                            )}
                            {isCurrent && (
                              <span className="text-xs text-muted-foreground">
                                · {formatTime(currentTime - chapter.startTime)} / {formatTime(chapter.duration)}
                              </span>
                            )}
                          </div>
                          {/* Per-chapter progress bar */}
                          {(isStarted || isCurrent) && (
                            <div className="mt-1.5 h-1 bg-muted rounded-full overflow-hidden w-full">
                              <div
                                className="h-full bg-primary rounded-full transition-all duration-500"
                                style={{ width: `${chPct}%` }}
                              />
                            </div>
                          )}
                        </div>

                        {/* Right: total chapter time */}
                        <span className="text-xs text-muted-foreground shrink-0 hidden sm:block">
                          {formatTime(chapter.startTime)}
                        </span>
                      </div>
                    )
                  })}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

// ── MetaRow ──────────────────────────────────────────────────────────────────

function MetaRow({ icon, label, value }: { icon: React.ReactNode; label: string; value: string }) {
  if (!value) return null
  return (
    <div className="flex items-center gap-2 text-muted-foreground">
      <span className="shrink-0 text-muted-foreground/70">{icon}</span>
      <span className="text-muted-foreground/70 shrink-0">{label}:</span>
      <span className="font-medium text-foreground truncate">{value}</span>
    </div>
  )
}
