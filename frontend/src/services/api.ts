// API client configuration

import axios from 'axios'
import type { AxiosRequestConfig } from 'axios'
import { API_BASE_URL } from '../config/env'

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

// ---- Token refresh helpers ----

let isRefreshing = false
let refreshSubscribers: ((token: string) => void)[] = []

function subscribeTokenRefresh(cb: (token: string) => void) {
  refreshSubscribers.push(cb)
}

function onTokenRefreshed(newToken: string) {
  refreshSubscribers.forEach((cb) => cb(newToken))
  refreshSubscribers = []
}

function clearAuthAndRedirect() {
  localStorage.removeItem('access_token')
  localStorage.removeItem('refresh_token')
  // Update the redux-persist snapshot so the page reload rehydrates as logged-out
  try {
    const persistKey = 'persist:audion-root'
    const raw = localStorage.getItem(persistKey)
    if (raw) {
      const persisted = JSON.parse(raw)
      persisted.auth = JSON.stringify({
        isAuthenticated: false,
        user: null,
        token: null,
        refreshToken: null,
        loading: false,
        error: null,
      })
      localStorage.setItem(persistKey, JSON.stringify(persisted))
    }
  } catch {
    localStorage.removeItem('persist:audion-root')
  }
  // Signal in-page listeners (e.g. App.tsx) to dispatch logout()
  window.dispatchEvent(new CustomEvent('auth:expired'))
  window.location.href = '/login'
}

async function refreshAccessToken(): Promise<string> {
  const refreshToken = localStorage.getItem('refresh_token')
  if (!refreshToken) throw new Error('No refresh token')

  const response = await axios.post(
    `${API_BASE_URL}/auth/refresh`,
    { refresh_token: refreshToken },
    { headers: { 'Content-Type': 'application/json' } }
  )

  const newAccessToken: string = response.data.access_token
  const newRefreshToken: string | undefined = response.data.refresh_token

  localStorage.setItem('access_token', newAccessToken)
  if (newRefreshToken) {
    localStorage.setItem('refresh_token', newRefreshToken)
  }

  return newAccessToken
}

// ---- Request interceptor: attach JWT ----

api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => Promise.reject(error)
)

// ---- Response interceptor: handle 401 with refresh ----

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config as AxiosRequestConfig & { _retry?: boolean }

    if (error.response?.status === 401 && !originalRequest._retry) {
      // Don't try to refresh the refresh endpoint itself (avoid loops)
      if (originalRequest.url?.includes('/auth/refresh')) {
        clearAuthAndRedirect()
        return Promise.reject(error)
      }

      if (isRefreshing) {
        // Queue this request until refresh completes
        return new Promise((resolve) => {
          subscribeTokenRefresh((newToken: string) => {
            if (originalRequest.headers) {
              originalRequest.headers.Authorization = `Bearer ${newToken}`
            }
            resolve(api(originalRequest))
          })
        })
      }

      originalRequest._retry = true
      isRefreshing = true

      try {
        const newToken = await refreshAccessToken()
        isRefreshing = false
        onTokenRefreshed(newToken)

        if (originalRequest.headers) {
          originalRequest.headers.Authorization = `Bearer ${newToken}`
        }
        return api(originalRequest)
      } catch (refreshError) {
        isRefreshing = false
        refreshSubscribers = []
        clearAuthAndRedirect()
        return Promise.reject(refreshError)
      }
    }

    return Promise.reject(error)
  }
)

export default api
