/**
 * AudiobookList Component
 * 
 * Displays a grid of audiobook cards using Redux state.
 * Supports filtering and searching through the store.
 */

import AudiobookCard from './AudiobookCard'
import { useAppSelector, selectFilteredAudiobooks } from '@/store'

export default function AudiobookList() {
  const audiobooks = useAppSelector(selectFilteredAudiobooks)
  
  if (audiobooks.length === 0) {
    return (
      <div className="text-center py-12 text-muted-foreground">
        <p>No audiobooks found</p>
      </div>
    )
  }
  
  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-4">
      {audiobooks.map((book) => (
        <AudiobookCard
          key={book.id}
          id={book.id}
          title={book.title}
          author={book.author}
          duration={book.duration}
          coverImage={book.coverImage}
          genre={book.genre}
        />
      ))}
    </div>
  )
}
