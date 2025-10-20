// Upload type definitions

export interface UploadResponse {
  id: string
  fileName: string
  fileSize: number
  status: 'pending' | 'processing' | 'completed' | 'failed'
  message?: string
}

export interface UploadProgress {
  uploadId: string
  progress: number
  status: string
}
