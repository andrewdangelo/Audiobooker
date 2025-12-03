/**
 * Demo Audiobook Data
 * 
 * Sample audiobooks for demonstration purposes.
 * These will be replaced with real API data in production.
 */

export interface DemoBook {
  id: string
  title: string
  author: string
  description: string
  coverImage?: string
  duration: number // in seconds
  chapters: DemoChapter[]
  audioUrl: string
  narrator?: string
  publishedYear?: number
  genre?: string
}

export interface DemoChapter {
  id: string
  title: string
  startTime: number // in seconds
  duration: number
}

// Demo audiobooks
export const demoBooks: DemoBook[] = [
  {
    id: 'demo-great-gatsby',
    title: 'The Great Gatsby',
    author: 'F. Scott Fitzgerald',
    narrator: 'Jake Gyllenhaal',
    description: 'The Great Gatsby is a 1925 novel by American writer F. Scott Fitzgerald. Set in the Jazz Age on Long Island, near New York City, the novel depicts first-person narrator Nick Carraway\'s interactions with mysterious millionaire Jay Gatsby and Gatsby\'s obsession to reunite with his former lover, Daisy Buchanan.',
    duration: 17820, // ~4.95 hours in seconds
    publishedYear: 1925,
    genre: 'Classic Fiction',
    audioUrl: 'https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3',
    chapters: [
      { id: 'ch1', title: 'Chapter 1: In My Younger and More Vulnerable Years', startTime: 0, duration: 1980 },
      { id: 'ch2', title: 'Chapter 2: About Half Way Between West Egg and New York', startTime: 1980, duration: 1620 },
      { id: 'ch3', title: 'Chapter 3: There Was Music From My Neighbor\'s House', startTime: 3600, duration: 2160 },
      { id: 'ch4', title: 'Chapter 4: On Sunday Morning', startTime: 5760, duration: 2340 },
      { id: 'ch5', title: 'Chapter 5: When I Came Home to West Egg', startTime: 8100, duration: 1980 },
      { id: 'ch6', title: 'Chapter 6: About This Time', startTime: 10080, duration: 1800 },
      { id: 'ch7', title: 'Chapter 7: It Was When Curiosity About Gatsby', startTime: 11880, duration: 2700 },
      { id: 'ch8', title: 'Chapter 8: I Couldn\'t Sleep All Night', startTime: 14580, duration: 1800 },
      { id: 'ch9', title: 'Chapter 9: After Two Years I Remember', startTime: 16380, duration: 1440 },
    ]
  },
  {
    id: 'demo-pride-prejudice',
    title: 'Pride and Prejudice',
    author: 'Jane Austen',
    narrator: 'Rosamund Pike',
    description: 'Pride and Prejudice is an 1813 novel of manners by Jane Austen. The novel follows the character development of Elizabeth Bennet, the dynamic protagonist of the book who learns about the repercussions of hasty judgments and comes to appreciate the difference between superficial goodness and actual goodness.',
    duration: 43200, // ~12 hours
    publishedYear: 1813,
    genre: 'Classic Romance',
    audioUrl: 'https://www.soundhelix.com/examples/mp3/SoundHelix-Song-2.mp3',
    chapters: [
      { id: 'ch1', title: 'Chapter 1', startTime: 0, duration: 720 },
      { id: 'ch2', title: 'Chapter 2', startTime: 720, duration: 600 },
      { id: 'ch3', title: 'Chapter 3', startTime: 1320, duration: 840 },
    ]
  },
  {
    id: 'demo-1984',
    title: '1984',
    author: 'George Orwell',
    narrator: 'Simon Prebble',
    description: '1984 is a dystopian social science fiction novel and cautionary tale by English writer George Orwell. It was published on 8 June 1949. Thematically, it centres on the consequences of totalitarianism, mass surveillance, and repressive regimentation of people and behaviours within society.',
    duration: 41400, // ~11.5 hours
    publishedYear: 1949,
    genre: 'Dystopian Fiction',
    audioUrl: 'https://www.soundhelix.com/examples/mp3/SoundHelix-Song-3.mp3',
    chapters: [
      { id: 'ch1', title: 'Part One: Chapter 1', startTime: 0, duration: 2400 },
      { id: 'ch2', title: 'Part One: Chapter 2', startTime: 2400, duration: 1800 },
      { id: 'ch3', title: 'Part One: Chapter 3', startTime: 4200, duration: 1500 },
    ]
  }
]

// Helper to get a book by ID
export function getBookById(id: string): DemoBook | undefined {
  return demoBooks.find(book => book.id === id)
}

// Helper to format duration
export function formatDuration(seconds: number): string {
  const hours = Math.floor(seconds / 3600)
  const minutes = Math.floor((seconds % 3600) / 60)
  
  if (hours > 0) {
    return `${hours}h ${minutes}m`
  }
  return `${minutes}m`
}
