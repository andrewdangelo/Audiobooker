/**
 * Audiobook Service
 *
 * Provides typed helpers for the Audiobook Library endpoints via the API proxy.
 *
 *   Frontend  →  Proxy (/backend/{path})  →  Backend service (/api/v1/{path})
 *
 * For full backend coverage see backendService.ts.
 * This file is kept as a convenience wrapper used by the audiobooksSlice.
 */

import api from './api'
import { AudiobookCreate } from '../types/audiobook'
import type { Audiobook, AudiobookChapter } from '../store/slices/audiobooksSlice'

/** All backend library routes go through this proxy segment */
const LIBRARY = '/backend/audiobooks'

// ---------------------------------------------------------------------------
// Normalizer — maps the backend's snake_case shape to the frontend's camelCase
// ---------------------------------------------------------------------------
function normalizeBook(raw: Record<string, unknown>): Audiobook {
  const rawChapters = (raw.chapters ?? []) as Array<Record<string, unknown>>
  const chapters: AudiobookChapter[] = rawChapters.map((ch) => ({
    id: String(ch.id ?? ch._id ?? ''),
    title: String(ch.title ?? ''),
    startTime: Number(ch.start_time ?? ch.startTime ?? 0),
    duration: Number(ch.duration ?? 0),
  }))

  return {
    id: String(raw.id ?? raw._id ?? ''),
    title: String(raw.title ?? ''),
    author: String(raw.author ?? ''),
    description: raw.description as string | undefined,
    coverImage: (raw.cover_image_url ?? raw.coverImage) as string | undefined,
    duration: Number(raw.duration ?? 0),
    audioUrl: (raw.audio_url ?? raw.audioUrl ?? '') as string,
    narrator: raw.narrator as string | undefined,
    publishedYear: (raw.published_year ?? raw.publishedYear) as number | undefined,
    genre: raw.genre as string | undefined,
    chapters,
    progress: Number(raw.progress ?? 0),
    status: (raw.status as 'draft' | 'processing' | 'completed' | 'failed' | undefined) ?? 'completed',
    isBookmarked: Boolean(raw.is_bookmarked ?? raw.isBookmarked ?? false),
    createdAt: raw.created_at as string | undefined,
    updatedAt: raw.updated_at as string | undefined,
    lastPlayedAt: raw.last_played_at as string | undefined,
    // Premium (theatrical) edition fields
    isPremium: Boolean(raw.is_premium ?? raw.isPremium ?? false),
    purchaseType: ((raw.purchase_type ?? raw.purchaseType ?? 'basic') as 'basic' | 'premium'),
    // TODO(back-end): When the PDF processor starts returning draft conversion
    // payloads, map the metadata/voice-selection job state into `conversion`.
    conversion: null,
  }
}

export const audiobookService = {
  /**
   * GET /audiobooks — fetch all audiobooks in the user's library.
   * @param userId  Required by the backend (query param)
   */
  async getAll(userId: string): Promise<Audiobook[]> {
    const response = await api.get(LIBRARY, { params: { user_id: userId } })
    // Backend returns { books: [...], total, page, pages }
    const raw: unknown[] = response.data?.books ?? response.data ?? []
    return raw.map((b) => normalizeBook(b as Record<string, unknown>))
  },

  /**
   * GET /audiobooks/{id} — fetch a single audiobook with chapter / progress data.
   */
  async getById(id: string, userId: string): Promise<Audiobook> {
    const response = await api.get(`${LIBRARY}/${id}`, { params: { user_id: userId } })
    return normalizeBook(response.data as Record<string, unknown>)
  },

  /**
   * POST /audiobooks — create a new audiobook record (after upload).
   */
  async create(data: AudiobookCreate, userId: string): Promise<Audiobook> {
    const response = await api.post(LIBRARY, data, { params: { user_id: userId } })
    return response.data
  },

  /**
   * PATCH /audiobooks/{id} — update audiobook metadata.
   */
  async update(id: string, updates: Partial<Audiobook>, userId: string): Promise<Audiobook> {
    const response = await api.patch(`${LIBRARY}/${id}`, updates, { params: { user_id: userId } })
    return response.data
  },

  /**
   * DELETE /audiobooks/{id} — remove audiobook from library.
   */
  async delete(id: string, userId: string): Promise<void> {
    await api.delete(`${LIBRARY}/${id}`, { params: { user_id: userId } })
  },

  /**
   * Returns the direct audio streaming URL for an audiobook.
   * Used by the audio player to load the audio source.
   */
  getAudioUrl(id: string): string {
    return `${api.defaults.baseURL}/backend/audiobooks/${id}/audio`
  },
}

