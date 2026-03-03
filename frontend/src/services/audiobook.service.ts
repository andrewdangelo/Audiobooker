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
import { Audiobook, AudiobookCreate } from '../types/audiobook'

/** All backend library routes go through this proxy segment */
const LIBRARY = '/backend/audiobooks'

export const audiobookService = {
  /**
   * GET /audiobooks — fetch all audiobooks in the user's library.
   * @param userId  Required by the backend (query param)
   */
  async getAll(userId: string): Promise<Audiobook[]> {
    const response = await api.get(LIBRARY, { params: { user_id: userId } })
    // Backend returns { books: [...], total, page, pages }
    return response.data?.books ?? response.data
  },

  /**
   * GET /audiobooks/{id} — fetch a single audiobook with chapter / progress data.
   */
  async getById(id: string, userId: string): Promise<Audiobook> {
    const response = await api.get(`${LIBRARY}/${id}`, { params: { user_id: userId } })
    return response.data
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

