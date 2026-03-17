// Environment configuration

// API Base URL - points to API proxy which routes to microservices
export const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8009/api/v1/audiobooker_proxy'

export const APP_NAME = import.meta.env.VITE_APP_NAME || 'Audion'
export const MAX_FILE_SIZE = parseInt(import.meta.env.VITE_MAX_FILE_SIZE || '52428800')

// Stripe Configuration (publishable key fetched from payment service)
export const STRIPE_PUBLISHABLE_KEY = import.meta.env.VITE_STRIPE_PUBLISHABLE_KEY || ''

export const isDevelopment = import.meta.env.DEV
export const isProduction = import.meta.env.PROD
