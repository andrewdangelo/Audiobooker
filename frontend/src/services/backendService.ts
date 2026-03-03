/**
 * Backend Service
 *
 * All calls to the Backend microservice are routed through the API proxy:
 *
 *   Frontend  →  Proxy (/backend/{path})  →  Backend service (/api/v1/{path})
 *
 * The proxy base URL is set in frontend/src/config/env.ts  (VITE_API_URL or
 * http://localhost:8000/api/v1/audiobooker_proxy).
 *
 * Covers:
 *  - User Management          (/users/*)
 *  - Audiobook Library        (/audiobooks/*)
 *  - Store & Marketplace      (/store/*)
 *  - Cart & Checkout          (/cart/*)
 *  - Publishing & Listings    (/store/listings/*)
 *  - Permissions              (/users/me/permissions, /users/me/usage)
 *  - Playback & Progress      (/audiobooks/{id}/audio, /progress, /bookmarks …)
 *  - Search                   (/search, /recommendations)
 *  - Notifications            (/notifications/*)
 */

import api from './api'

// ============================================================================
// PATH PREFIX
// ============================================================================

/** All backend routes are forwarded via this proxy segment */
const B = '/backend'

// ============================================================================
// TYPES
// ============================================================================

export interface UserProfile {
  id: string
  email: string
  first_name: string
  last_name?: string
  avatar_url?: string
  role?: string
  created_at?: string
}

export interface UserCredits {
  credits: number
  credits_used: number
  credits_expiring?: number
  expiry_date?: string
}

export interface UserStats {
  total_audiobooks: number
  hours_listened: number
  books_completed: number
  favorite_genre?: string
}

export interface ActivityItem {
  type: string
  title: string
  timestamp: string
}

export interface ContinueListeningItem {
  id: string
  title: string
  progress: number
  last_played_at: string
}

export interface BookshelfItem {
  id: string
  title: string
  added_at: string
}

// --- Library ---

export interface LibraryBook {
  id: string
  title: string
  author: string
  duration: number
  cover_image_url?: string
  progress?: number
}

export interface LibraryResponse {
  books: LibraryBook[]
  total: number
  page: number
  pages: number
}

// --- Store ---

export interface StoreBookBasic {
  id: string
  title: string
  author: string
  price: number
  credits: number
  genre?: string
  rating?: number
  cover_image_url?: string
}

export interface StoreBookDetailed extends StoreBookBasic {
  narrator?: string
  description?: string
  synopsis?: string
  duration?: number
  chapters?: ChapterInfo[]
  categories?: string[]
  review_count?: number
  sample_audio_url?: string
}

export interface StoreCatalogResponse {
  books: StoreBookBasic[]
  total: number
  page: number
}

export interface ChapterInfo {
  id: string
  title: string
  start_time: number
  duration: number
  chapter_number?: number
}

// --- Playback ---

export interface AudioUrlResponse {
  audio_url: string
  format: string
  duration: number
}

export interface ProgressResponse {
  position: number
  progress: number
  last_played_at: string
}

export interface Bookmark {
  id: string
  position: number
  note?: string
  created_at: string
}

// --- Notifications ---

export interface Notification {
  id: string
  type: string
  title: string
  message: string
  read: boolean
  created_at: string
}

export interface NotificationsResponse {
  notifications: Notification[]
  unread_count: number
}

// --- Search ---

export interface SearchResult {
  id: string
  title: string
  author: string
  type: 'library' | 'store'
}

export interface SearchResponse {
  results: SearchResult[]
  total: number
}

// --- Permissions ---

export interface UserPermissions {
  role: string
  tier: string
  permissions: string[]
  limits: {
    max_uploads: number
    max_storage: number
    max_devices: number
    max_published_books: number
  }
  is_admin: boolean
}

export interface UserUsage {
  uploads: number
  storage_used: number
  devices_connected: number
  published_books: number
}

// --- Publishing ---

export interface ListingBasic {
  id: string
  title: string
  status: string
  price: number
  total_sales?: number
  rating?: number
  published_at?: string
}

export interface ListingDetailed extends ListingBasic {
  audiobook_id: string
  revenue?: number
}

// ============================================================================
// USER MANAGEMENT
// ============================================================================

export const userService = {
  /** GET /users/me */
  async getProfile(userId: string): Promise<UserProfile> {
    const res = await api.get(`${B}/users/me`, { params: { user_id: userId } })
    return res.data
  },

  /** GET /users/me/credits */
  async getCredits(userId: string): Promise<UserCredits> {
    const res = await api.get(`${B}/users/me/credits`, { params: { user_id: userId } })
    return res.data
  },

  /** GET /users/{userId}/stats */
  async getStats(userId: string): Promise<UserStats> {
    const res = await api.get(`${B}/users/${userId}/stats`)
    return res.data
  },

  /** GET /users/{userId}/activity */
  async getActivity(userId: string, limit = 10): Promise<{ activities: ActivityItem[] }> {
    const res = await api.get(`${B}/users/${userId}/activity`, { params: { limit } })
    return res.data
  },

  /** GET /users/{userId}/continue-listening */
  async getContinueListening(userId: string): Promise<{ audiobooks: ContinueListeningItem[] }> {
    const res = await api.get(`${B}/users/${userId}/continue-listening`)
    return res.data
  },

  /** GET /users/{userId}/bookshelf */
  async getBookshelf(userId: string): Promise<{ audiobooks: BookshelfItem[] }> {
    const res = await api.get(`${B}/users/${userId}/bookshelf`)
    return res.data
  },

  /** GET /users/me/permissions */
  async getPermissions(userId: string): Promise<UserPermissions> {
    const res = await api.get(`${B}/users/me/permissions`, { params: { user_id: userId } })
    return res.data
  },

  /** GET /users/me/usage */
  async getUsage(userId: string): Promise<UserUsage> {
    const res = await api.get(`${B}/users/me/usage`, { params: { user_id: userId } })
    return res.data
  },
}

// ============================================================================
// AUDIOBOOK LIBRARY
// ============================================================================

export const libraryService = {
  /** GET /audiobooks — user's library */
  async getAll(
    userId: string,
    options?: { page?: number; limit?: number; sort?: string },
  ): Promise<LibraryResponse> {
    const res = await api.get(`${B}/audiobooks`, {
      params: { user_id: userId, ...options },
    })
    return res.data
  },

  /** GET /audiobooks/{id} */
  async getById(bookId: string, userId: string) {
    const res = await api.get(`${B}/audiobooks/${bookId}`, {
      params: { user_id: userId },
    })
    return res.data
  },

  /** POST /audiobooks */
  async create(userId: string, data: { title: string; file_id?: string }) {
    const res = await api.post(`${B}/audiobooks`, data, {
      params: { user_id: userId },
    })
    return res.data
  },

  /** PATCH /audiobooks/{id} */
  async update(bookId: string, userId: string, updates: Record<string, unknown>) {
    const res = await api.patch(`${B}/audiobooks/${bookId}`, updates, {
      params: { user_id: userId },
    })
    return res.data
  },

  /** DELETE /audiobooks/{id} */
  async remove(bookId: string, userId: string) {
    await api.delete(`${B}/audiobooks/${bookId}`, { params: { user_id: userId } })
  },
}

// ============================================================================
// STORE / MARKETPLACE
// ============================================================================

export const storeService = {
  /** GET /store/catalog */
  async getCatalog(params?: {
    genre?: string
    sort?: string
    page?: number
    limit?: number
  }): Promise<StoreCatalogResponse> {
    const res = await api.get(`${B}/store/catalog`, { params })
    return res.data
  },

  /** GET /store/books/{id} */
  async getBookDetails(bookId: string): Promise<StoreBookDetailed> {
    const res = await api.get(`${B}/store/books/${bookId}`)
    return res.data
  },

  /** GET /store/featured */
  async getFeatured(): Promise<StoreCatalogResponse> {
    const res = await api.get(`${B}/store/featured`)
    return res.data
  },

  /** GET /store/new-releases */
  async getNewReleases(): Promise<StoreCatalogResponse> {
    const res = await api.get(`${B}/store/new-releases`)
    return res.data
  },

  /** GET /store/bestsellers */
  async getBestsellers(): Promise<StoreCatalogResponse> {
    const res = await api.get(`${B}/store/bestsellers`)
    return res.data
  },

  /** GET /store/books/{id}/related */
  async getRelated(bookId: string): Promise<StoreCatalogResponse> {
    const res = await api.get(`${B}/store/books/${bookId}/related`)
    return res.data
  },

  /** POST /store/purchase */
  async purchase(userId: string, bookId: string, paymentMethod: 'credits' | 'card') {
    const res = await api.post(
      `${B}/store/purchase`,
      { book_id: bookId, payment_method: paymentMethod },
      { params: { user_id: userId } },
    )
    return res.data
  },
}

// ============================================================================
// CART
// ============================================================================

export const cartApiService = {
  /** GET /cart */
  async getCart(userId: string) {
    const res = await api.get(`${B}/cart`, { params: { user_id: userId } })
    return res.data
  },

  /** POST /cart/items */
  async addItem(userId: string, bookId: string, quantity = 1) {
    const res = await api.post(
      `${B}/cart/items`,
      { book_id: bookId, quantity },
      { params: { user_id: userId } },
    )
    return res.data
  },

  /** DELETE /cart/items/{bookId} */
  async removeItem(userId: string, bookId: string) {
    await api.delete(`${B}/cart/items/${bookId}`, { params: { user_id: userId } })
  },

  /** PATCH /cart/items/{bookId} */
  async updateItemQuantity(userId: string, bookId: string, quantity: number) {
    const res = await api.patch(
      `${B}/cart/items/${bookId}`,
      { quantity },
      { params: { user_id: userId } },
    )
    return res.data
  },

  /** POST /cart/sync */
  async sync(userId: string, items: unknown[]) {
    const res = await api.post(
      `${B}/cart/sync`,
      { items },
      { params: { user_id: userId } },
    )
    return res.data
  },

  /** POST /cart/validate */
  async validate(userId: string) {
    const res = await api.post(`${B}/cart/validate`, {}, { params: { user_id: userId } })
    return res.data
  },

  /** DELETE /cart */
  async clearCart(userId: string) {
    await api.delete(`${B}/cart`, { params: { user_id: userId } })
  },
}

// ============================================================================
// PUBLISHING & LISTINGS
// ============================================================================

export const publishingService = {
  /** GET /store/listings/my-listings */
  async getMyListings(
    userId: string,
    params?: { status?: string; page?: number; limit?: number },
  ): Promise<{ listings: ListingBasic[]; total: number }> {
    const res = await api.get(`${B}/store/listings/my-listings`, {
      params: { user_id: userId, ...params },
    })
    return res.data
  },

  /** POST /store/listings */
  async createListing(userId: string, data: Record<string, unknown>) {
    const res = await api.post(`${B}/store/listings`, data, {
      params: { user_id: userId },
    })
    return res.data
  },

  /** GET /store/listings/{id} */
  async getListing(listingId: string, userId: string): Promise<ListingDetailed> {
    const res = await api.get(`${B}/store/listings/${listingId}`, {
      params: { user_id: userId },
    })
    return res.data
  },

  /** PATCH /store/listings/{id} */
  async updateListing(listingId: string, userId: string, updates: Record<string, unknown>) {
    const res = await api.patch(`${B}/store/listings/${listingId}`, updates, {
      params: { user_id: userId },
    })
    return res.data
  },

  /** DELETE /store/listings/{id} */
  async deleteListing(listingId: string, userId: string) {
    await api.delete(`${B}/store/listings/${listingId}`, { params: { user_id: userId } })
  },

  /** POST /store/listings/{id}/cover — multipart upload */
  async uploadCover(listingId: string, userId: string, file: File) {
    const formData = new FormData()
    formData.append('file', file)
    const res = await api.post(`${B}/store/listings/${listingId}/cover`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      params: { user_id: userId },
    })
    return res.data
  },
}

// ============================================================================
// PLAYBACK & PROGRESS
// ============================================================================

export const playbackService = {
  /** GET /audiobooks/{id}/audio */
  async getAudioUrl(bookId: string, userId: string): Promise<AudioUrlResponse> {
    const res = await api.get(`${B}/audiobooks/${bookId}/audio`, {
      params: { user_id: userId },
    })
    return res.data
  },

  /** POST /audiobooks/{id}/progress */
  async saveProgress(
    bookId: string,
    userId: string,
    position: number,
    duration: number,
    chapterId?: string,
  ) {
    const res = await api.post(
      `${B}/audiobooks/${bookId}/progress`,
      { position, duration, chapter_id: chapterId },
      { params: { user_id: userId } },
    )
    return res.data
  },

  /** GET /audiobooks/{id}/progress */
  async getProgress(bookId: string, userId: string): Promise<ProgressResponse> {
    const res = await api.get(`${B}/audiobooks/${bookId}/progress`, {
      params: { user_id: userId },
    })
    return res.data
  },

  /** POST /audiobooks/{id}/bookmarks */
  async createBookmark(
    bookId: string,
    userId: string,
    position: number,
    note?: string,
  ): Promise<Bookmark> {
    const res = await api.post(
      `${B}/audiobooks/${bookId}/bookmarks`,
      { position, note },
      { params: { user_id: userId } },
    )
    return res.data
  },

  /** GET /audiobooks/{id}/bookmarks */
  async getBookmarks(bookId: string, userId: string): Promise<{ bookmarks: Bookmark[] }> {
    const res = await api.get(`${B}/audiobooks/${bookId}/bookmarks`, {
      params: { user_id: userId },
    })
    return res.data
  },

  /** GET /audiobooks/{id}/chapters */
  async getChapters(bookId: string, userId: string): Promise<{ chapters: ChapterInfo[] }> {
    const res = await api.get(`${B}/audiobooks/${bookId}/chapters`, {
      params: { user_id: userId },
    })
    return res.data
  },

  /** POST /audiobooks/{id}/complete */
  async markComplete(bookId: string, userId: string) {
    const res = await api.post(
      `${B}/audiobooks/${bookId}/complete`,
      {},
      { params: { user_id: userId } },
    )
    return res.data
  },
}

// ============================================================================
// SEARCH & DISCOVERY
// ============================================================================

export const searchService = {
  /** GET /search */
  async search(
    query: string,
    userId: string,
    scope: 'all' | 'library' | 'store' = 'all',
    limit = 20,
  ): Promise<SearchResponse> {
    const res = await api.get(`${B}/search`, {
      params: { q: query, user_id: userId, scope, limit },
    })
    return res.data
  },

  /** GET /recommendations */
  async getRecommendations(userId: string) {
    const res = await api.get(`${B}/recommendations`, { params: { user_id: userId } })
    return res.data
  },
}

// ============================================================================
// NOTIFICATIONS
// ============================================================================

export const notificationsService = {
  /** GET /notifications */
  async getNotifications(
    userId: string,
    params?: { unread?: boolean; limit?: number },
  ): Promise<NotificationsResponse> {
    const res = await api.get(`${B}/notifications`, {
      params: { user_id: userId, ...params },
    })
    return res.data
  },

  /** PATCH /notifications/{id}/read */
  async markRead(notificationId: string, userId: string) {
    const res = await api.patch(
      `${B}/notifications/${notificationId}/read`,
      {},
      { params: { user_id: userId } },
    )
    return res.data
  },

  /** POST /notifications/mark-all-read */
  async markAllRead(userId: string) {
    const res = await api.post(
      `${B}/notifications/mark-all-read`,
      {},
      { params: { user_id: userId } },
    )
    return res.data
  },
}
