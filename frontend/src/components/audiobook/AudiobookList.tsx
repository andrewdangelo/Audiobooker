/**
 * AudiobookList Component
 * 
 * Displays a grid of audiobook cards.
 * Currently shows demo books, will integrate with API later.
 */

import AudiobookCard from './AudiobookCard'
import { demoBooks } from '@/data/demoBooks'

export default function AudiobookList() {
  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-4">
      {demoBooks.map((book) => (
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
