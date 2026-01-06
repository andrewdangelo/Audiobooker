// Environment configuration

export const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'
export const APP_NAME = import.meta.env.VITE_APP_NAME || 'Audion'
export const MAX_FILE_SIZE = parseInt(import.meta.env.VITE_MAX_FILE_SIZE || '52428800')

export const isDevelopment = import.meta.env.DEV
export const isProduction = import.meta.env.PROD
