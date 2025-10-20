// Audiobook service for API calls

import api from './api'
import { Audiobook, AudiobookCreate } from '../types/audiobook'

export const audiobookService = {
  // Get all audiobooks
  async getAll(): Promise<Audiobook[]> {
    const response = await api.get('/audiobooks')
    return response.data
  },

  // Get single audiobook by ID
  async getById(id: string): Promise<Audiobook> {
    const response = await api.get(`/audiobooks/${id}`)
    return response.data
  },

  // Create new audiobook
  async create(data: AudiobookCreate): Promise<Audiobook> {
    const response = await api.post('/audiobooks', data)
    return response.data
  },

  // Delete audiobook
  async delete(id: string): Promise<void> {
    await api.delete(`/audiobooks/${id}`)
  },

  // Get audiobook audio URL
  getAudioUrl(id: string): string {
    return `${api.defaults.baseURL}/audiobooks/${id}/audio`
  },
}
