import { describe, expect, it } from 'vitest'
import { normalizeStoreBook } from '../storeSlice'

describe('normalizeStoreBook', () => {
  it('maps snake_case API fields to StoreBook', () => {
    const book = normalizeStoreBook({
      id: 'b1',
      title: 'Test',
      author: 'A. Author',
      description: 'Desc',
      cover_image_url: 'https://example.com/cover.jpg',
      duration: 3600,
      narrator: 'Narrator',
      published_year: 2024,
      genre: 'Fiction',
      rating: 4.5,
      review_count: 10,
      price: 14.99,
      credits: 2,
      original_price: 19.99,
      is_on_sale: true,
      is_premium: true,
      premium_price: 24.99,
      premium_credits: 3,
      language: 'en',
      release_date: '2024-01-01',
      publisher: 'Pub',
      tags: ['a', 'b'],
      chapters: [
        {
          id: 'c1',
          title: 'Ch1',
          duration_seconds: 100,
          order: 0,
        },
      ],
      characters: [{ name: 'Hero', voice_actor: 'VA1', sample_audio_url: 'https://x/s.mp3' }],
    })

    expect(book.id).toBe('b1')
    expect(book.coverImage).toBe('https://example.com/cover.jpg')
    expect(book.publishedYear).toBe(2024)
    expect(book.price).toBe(1499)
    expect(book.originalPrice).toBe(1999)
    expect(book.premiumPrice).toBe(2499)
    expect(book.premiumCredits).toBe(3)
    expect(book.chapters[0]).toMatchObject({ id: 'c1', title: 'Ch1', duration: 100, order: 0 })
    expect(book.characters[0]).toMatchObject({
      name: 'Hero',
      voiceActor: 'VA1',
      sampleAudioUrl: 'https://x/s.mp3',
    })
  })

  it('uses _id and credits_required fallbacks', () => {
    const book = normalizeStoreBook({
      _id: 'mongo1',
      title: 'T',
      author: 'A',
      description: '',
      credits_required: 5,
    })
    expect(book.id).toBe('mongo1')
    expect(book.credits).toBe(5)
    expect(book.chapters).toEqual([])
    expect(book.characters).toEqual([])
  })
})
