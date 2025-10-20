// Application constants

export const MAX_FILE_SIZE = 52428800 // 50MB in bytes
export const ALLOWED_FILE_TYPES = ['application/pdf']
export const AUDIO_FORMATS = ['mp3', 'wav']

export const CONVERSION_STATUS = {
  PENDING: 'pending',
  PROCESSING: 'processing',
  COMPLETED: 'completed',
  FAILED: 'failed',
} as const

export const ROUTES = {
  HOME: '/',
  DASHBOARD: '/dashboard',
  UPLOAD: '/upload',
  LIBRARY: '/library',
} as const
