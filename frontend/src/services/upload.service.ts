// Upload service for file uploads

import api from './api'
import { UploadResponse } from '../types/upload'

export const uploadService = {
  // Upload PDF file
  async uploadPDF(file: File, onProgress?: (progress: number) => void): Promise<UploadResponse> {
    const formData = new FormData()
    formData.append('file', file)

    const response = await api.post('/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      onUploadProgress: (progressEvent) => {
        if (progressEvent.total && onProgress) {
          const progress = Math.round((progressEvent.loaded * 100) / progressEvent.total)
          onProgress(progress)
        }
      },
    })

    return response.data
  },

  // Get upload status
  async getStatus(uploadId: string) {
    const response = await api.get(`/upload/${uploadId}/status`)
    return response.data
  },
}
