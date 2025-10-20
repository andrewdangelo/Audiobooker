// Audiobook type definitions

export interface Audiobook {
  id: string
  title: string
  originalFileName: string
  duration?: number
  fileSize: number
  status: 'processing' | 'completed' | 'failed'
  audioUrl?: string
  createdAt: string
  updatedAt: string
}

export interface AudiobookCreate {
  title: string
  fileId: string
}

export interface AudiobookUpdate {
  title?: string
}
