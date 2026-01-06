/**
 * BookDetail Page
 * 
 * Displays detailed information about an audiobook with a play button
 * that opens the pop-out player.
 */

import { useParams, useNavigate } from 'react-router-dom'
import { Play, Clock, Calendar, BookOpen, ArrowLeft, Headphones } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { getBookById, formatDuration, DemoBook } from '@/data/demoBooks'
import { AudioState } from '@/hooks/useAudioSync'

export default function BookDetail() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  
  const book = id ? getBookById(id) : undefined
  
  if (!book) {
    return (
      <div className="container mx-auto px-4 py-16 text-center">
        <h1 className="text-2xl font-bold mb-4">Book Not Found</h1>
        <p className="text-muted-foreground mb-6">
          The audiobook you're looking for doesn't exist.
        </p>
        <Button onClick={() => navigate('/library')}>
          <ArrowLeft className="h-4 w-4 mr-2" />
          Back to Library
        </Button>
      </div>
    )
  }
  
  // Open pop-out player with book data
  const handlePlay = () => {
    const state: AudioState = {
      isPlaying: true, // Start playing immediately
      currentTime: 0,
      duration: book.duration,
      playbackRate: 1.0,
      audioUrl: book.audioUrl,
      title: book.title,
      coverImage: book.coverImage,
      currentChapter: book.chapters[0]?.title || 'Chapter 1',
      audiobookId: book.id
    }
    
    const stateParam = encodeURIComponent(JSON.stringify(state))
    const popoutUrl = `/player-popout?state=${stateParam}`
    
    // Calculate window position
    const width = 400
    const height = 550
    const left = window.screenX + window.outerWidth - width - 50
    const top = window.screenY + 100
    
    window.open(
      popoutUrl,
      'audion-popout',
      `width=${width},height=${height},left=${left},top=${top},resizable=yes,scrollbars=no`
    )
  }
  
  return (
    <div className="container mx-auto px-4 py-8">
      {/* Back Button */}
      <Button 
        variant="ghost" 
        onClick={() => navigate('/library')}
        className="mb-6"
      >
        <ArrowLeft className="h-4 w-4 mr-2" />
        Back to Library
      </Button>
      
      {/* Book Details */}
      <div className="grid md:grid-cols-[300px_1fr] gap-8">
        {/* Cover Art */}
        <div className="flex flex-col items-center">
          <div className="w-full max-w-[300px] aspect-[3/4] rounded-xl overflow-hidden shadow-2xl bg-gradient-to-br from-primary/20 to-primary/40 mb-6">
            {book.coverImage ? (
              <img
                src={book.coverImage}
                alt={book.title}
                className="w-full h-full object-cover"
              />
            ) : (
              <div className="w-full h-full flex items-center justify-center">
                <svg
                  className="w-32 h-32 text-primary/60"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={1.5}
                    d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253"
                  />
                </svg>
              </div>
            )}
          </div>
          
          {/* Play Button - Primary CTA */}
          <Button 
            size="lg" 
            onClick={handlePlay}
            className="w-full max-w-[300px] h-14 text-lg font-semibold shadow-lg hover:shadow-xl transition-all"
          >
            <Play className="h-6 w-6 mr-2" fill="currentColor" />
            Play Audiobook
          </Button>
        </div>
        
        {/* Book Info */}
        <div>
          {/* Genre Badge */}
          {book.genre && (
            <span className="inline-block px-3 py-1 text-sm font-medium bg-primary/10 text-primary rounded-full mb-3">
              {book.genre}
            </span>
          )}
          
          {/* Title */}
          <h1 className="text-4xl font-bold mb-2">{book.title}</h1>
          
          {/* Author */}
          <p className="text-xl text-muted-foreground mb-6">
            by {book.author}
          </p>
          
          {/* Meta Info */}
          <div className="flex flex-wrap gap-6 mb-8">
            <div className="flex items-center gap-2 text-muted-foreground">
              <Clock className="h-5 w-5" />
              <span>{formatDuration(book.duration)}</span>
            </div>
            
            {book.narrator && (
              <div className="flex items-center gap-2 text-muted-foreground">
                <Headphones className="h-5 w-5" />
                <span>Narrated by {book.narrator}</span>
              </div>
            )}
            
            {book.publishedYear && (
              <div className="flex items-center gap-2 text-muted-foreground">
                <Calendar className="h-5 w-5" />
                <span>{book.publishedYear}</span>
              </div>
            )}
            
            <div className="flex items-center gap-2 text-muted-foreground">
              <BookOpen className="h-5 w-5" />
              <span>{book.chapters.length} Chapters</span>
            </div>
          </div>
          
          {/* Description */}
          <div className="mb-8">
            <h2 className="text-xl font-semibold mb-3">About this book</h2>
            <p className="text-muted-foreground leading-relaxed">
              {book.description}
            </p>
          </div>
          
          {/* Chapters List */}
          <div>
            <h2 className="text-xl font-semibold mb-4">Chapters</h2>
            <div className="space-y-2">
              {book.chapters.map((chapter, index) => (
                <ChapterItem 
                  key={chapter.id}
                  index={index + 1}
                  title={chapter.title}
                  duration={chapter.duration}
                  onPlay={() => handlePlayChapter(book, chapter.startTime)}
                />
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

// Helper function to play from a specific chapter
function handlePlayChapter(book: DemoBook, startTime: number) {
  const chapterIndex = book.chapters.findIndex(ch => ch.startTime === startTime)
  const chapter = book.chapters[chapterIndex]
  
  const state: AudioState = {
    isPlaying: true,
    currentTime: startTime,
    duration: book.duration,
    playbackRate: 1.0,
    audioUrl: book.audioUrl,
    title: book.title,
    coverImage: book.coverImage,
    currentChapter: chapter?.title || `Chapter ${chapterIndex + 1}`,
    audiobookId: book.id
  }
  
  const stateParam = encodeURIComponent(JSON.stringify(state))
  const popoutUrl = `/player-popout?state=${stateParam}`
  
  const width = 400
  const height = 550
  const left = window.screenX + window.outerWidth - width - 50
  const top = window.screenY + 100
  
  window.open(
    popoutUrl,
    'audion-popout',
    `width=${width},height=${height},left=${left},top=${top},resizable=yes,scrollbars=no`
  )
}

// Chapter item component
interface ChapterItemProps {
  index: number
  title: string
  duration: number
  onPlay: () => void
}

function ChapterItem({ index, title, duration, onPlay }: ChapterItemProps) {
  return (
    <div className="flex items-center gap-4 p-3 rounded-lg hover:bg-muted/50 transition-colors group">
      <span className="text-sm font-medium text-muted-foreground w-8">
        {index.toString().padStart(2, '0')}
      </span>
      
      <div className="flex-1 min-w-0">
        <p className="font-medium truncate">{title}</p>
        <p className="text-sm text-muted-foreground">{formatDuration(duration)}</p>
      </div>
      
      <Button 
        variant="ghost" 
        size="icon"
        onClick={(e) => {
          e.stopPropagation()
          onPlay()
        }}
        className="opacity-0 group-hover:opacity-100 transition-opacity"
      >
        <Play className="h-4 w-4" fill="currentColor" />
      </Button>
    </div>
  )
}
