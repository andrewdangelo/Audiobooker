# Audiobooker Backend API Endpoints

Complete list of all API endpoints required for the Audiobooker frontend application.

## Table of Contents
- [Authentication & Authorization](#authentication--authorization)
- [User Management](#user-management)
- [Audiobook Library](#audiobook-library)
- [Store & Marketplace](#store--marketplace)
- [Cart & Checkout](#cart--checkout)
- [Publishing & Listings](#publishing--listings)
- [Payments & Subscriptions](#payments--subscriptions)
- [Permissions & Access Control](#permissions--access-control)
- [Audio Processing & Previews](#audio-processing--previews)
- [Playback & Progress](#playback--progress)
- [Search & Discovery](#search--discovery)
- [Notifications](#notifications)
- [Analytics (Publisher/Admin)](#analytics-publisheradmin)

---

## Authentication & Authorization

### POST /api/v1/auth/signup
**Purpose:** Create a new user account  
**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "securepassword",
  "name": "John Doe"
}
```
**Response:** 201 Created
```json
{
  "user": {
    "id": "user_123",
    "email": "user@example.com",
    "name": "John Doe",
    "role": "basic"
  },
  "token": "jwt_token_here"
}
```
**Source:** `src/pages/Signup.tsx`

---

### POST /api/v1/auth/login
**Purpose:** Authenticate user and return JWT token  
**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "password123"
}
```
**Response:** 200 OK
```json
{
  "user": {
    "id": "user_123",
    "email": "user@example.com",
    "name": "John Doe",
    "role": "premium"
  },
  "token": "jwt_token_here"
}
```
**Source:** `src/pages/Login.tsx`, `src/store/slices/authSlice.ts`

---

### POST /api/v1/auth/logout
**Purpose:** Invalidate user session/token  
**Headers:** `Authorization: Bearer {token}`  
**Response:** 200 OK
```json
{
  "message": "Logged out successfully"
}
```
**Source:** `src/components/layout/Navbar.tsx`, `src/store/slices/authSlice.ts`

---

### POST /api/v1/auth/change-password
**Purpose:** Change user password  
**Headers:** `Authorization: Bearer {token}`  
**Request Body:**
```json
{
  "currentPassword": "oldpassword",
  "newPassword": "newpassword"
}
```
**Response:** 200 OK
```json
{
  "message": "Password changed successfully"
}
```
**Source:** `src/pages/Settings.tsx`

---

### POST /api/v1/auth/forgot-password
**Purpose:** Request password reset email  
**Request Body:**
```json
{
  "email": "user@example.com"
}
```
**Response:** 200 OK
```json
{
  "message": "Password reset email sent"
}
```
**Source:** `src/pages/ForgotPassword.tsx`

---

### GET /api/v1/auth/me
**Purpose:** Get current authenticated user  
**Headers:** `Authorization: Bearer {token}`  
**Response:** 200 OK
```json
{
  "id": "user_123",
  "email": "user@example.com",
  "name": "John Doe",
  "role": "premium",
  "avatarUrl": "https://...",
  "credits": 50
}
```
**Source:** `src/components/layout/AppLayout.tsx`, `src/components/layout/Navbar.tsx`

---

## User Management

### GET /api/v1/users/me
**Purpose:** Get current user profile  
**Headers:** `Authorization: Bearer {token}`  
**Response:** 200 OK
```json
{
  "id": "user_123",
  "email": "user@example.com",
  "name": "John Doe",
  "avatarUrl": "https://...",
  "role": "premium",
  "createdAt": "2025-01-01T00:00:00Z"
}
```
**Source:** `src/components/layout/Navbar.tsx`

---

### POST /api/v1/users/me
**Purpose:** Update user profile  
**Headers:** `Authorization: Bearer {token}`  
**Request Body:**
```json
{
  "name": "Jane Doe",
  "email": "jane@example.com"
}
```
**Response:** 200 OK
```json
{
  "id": "user_123",
  "email": "jane@example.com",
  "name": "Jane Doe"
}
```
**Source:** `src/pages/Settings.tsx`

---

### POST /api/v1/users/me/avatar
**Purpose:** Upload user avatar image  
**Headers:** `Authorization: Bearer {token}`  
**Request:** Multipart form data with image file  
**Response:** 200 OK
```json
{
  "avatarUrl": "https://cdn.example.com/avatars/user_123.jpg"
}
```
**Source:** `src/pages/Settings.tsx`

---

### DELETE /api/v1/users/me
**Purpose:** Delete user account permanently  
**Headers:** `Authorization: Bearer {token}`  
**Response:** 204 No Content
**Source:** `src/pages/Settings.tsx`

---

### PATCH /api/v1/users/me/preferences
**Purpose:** Update user preferences (notifications, settings)  
**Headers:** `Authorization: Bearer {token}`  
**Request Body:**
```json
{
  "emailNotifications": true,
  "marketingEmails": false,
  "theme": "dark",
  "language": "en"
}
```
**Response:** 200 OK
**Source:** `src/pages/Settings.tsx`

---

### GET /api/v1/users/me/credits
**Purpose:** Get user's current credit balance  
**Headers:** `Authorization: Bearer {token}`  
**Response:** 200 OK
```json
{
  "credits": 50,
  "creditsUsed": 25,
  "creditsExpiring": 5,
  "expiryDate": "2025-12-31T00:00:00Z"
}
```
**Source:** `src/components/layout/Navbar.tsx`

---

### GET /api/v1/users/{userId}/stats
**Purpose:** Get user statistics for dashboard  
**Headers:** `Authorization: Bearer {token}`  
**Response:** 200 OK
```json
{
  "totalAudiobooks": 42,
  "hoursListened": 156.5,
  "booksCompleted": 12,
  "favoriteGenre": "Science Fiction"
}
```
**Source:** `src/pages/Dashboard.tsx`

---

### GET /api/v1/users/{userId}/activity
**Purpose:** Get recent user activity  
**Headers:** `Authorization: Bearer {token}`  
**Query Params:** `?limit=10`  
**Response:** 200 OK
```json
{
  "activities": [
    {
      "type": "completed",
      "title": "The Great Gatsby",
      "timestamp": "2025-01-15T10:30:00Z"
    }
  ]
}
```
**Source:** `src/pages/Dashboard.tsx`

---

### GET /api/v1/users/{userId}/continue-listening
**Purpose:** Get audiobooks user is currently listening to  
**Headers:** `Authorization: Bearer {token}`  
**Response:** 200 OK
```json
{
  "audiobooks": [
    {
      "id": "book_123",
      "title": "1984",
      "progress": 0.45,
      "lastPlayedAt": "2025-01-20T14:30:00Z"
    }
  ]
}
```
**Source:** `src/pages/Dashboard.tsx`

---

### GET /api/v1/users/{userId}/bookshelf
**Purpose:** Get user's saved/bookmarked audiobooks  
**Headers:** `Authorization: Bearer {token}`  
**Response:** 200 OK
```json
{
  "audiobooks": [
    {
      "id": "book_456",
      "title": "To Kill a Mockingbird",
      "addedAt": "2025-01-10T00:00:00Z"
    }
  ]
}
```
**Source:** `src/components/layout/Sidebar.tsx`

---

### GET /api/v1/users/{userId}/settings
**Purpose:** Get user settings  
**Headers:** `Authorization: Bearer {token}`  
**Response:** 200 OK
```json
{
  "theme": "dark",
  "language": "en",
  "autoplay": true,
  "playbackSpeed": 1.0
}
```
**Source:** `src/components/layout/Sidebar.tsx`

---

## Audiobook Library

### GET /api/v1/audiobooks
**Purpose:** Get user's audiobook library  
**Headers:** `Authorization: Bearer {token}`  
**Query Params:** `?page=1&limit=20&sort=recent`  
**Response:** 200 OK
```json
{
  "audiobooks": [
    {
      "id": "book_123",
      "title": "The Great Gatsby",
      "author": "F. Scott Fitzgerald",
      "duration": 14400,
      "coverImage": "https://...",
      "progress": 0.35
    }
  ],
  "total": 42,
  "page": 1,
  "pages": 3
}
```
**Source:** `src/store/slices/audiobooksSlice.ts`, `src/hooks/useAudiobooks.ts`

---

### GET /api/v1/audiobooks/{id}
**Purpose:** Get detailed audiobook information  
**Headers:** `Authorization: Bearer {token}`  
**Response:** 200 OK
```json
{
  "id": "book_123",
  "title": "The Great Gatsby",
  "author": "F. Scott Fitzgerald",
  "narrator": "Jake Gyllenhaal",
  "duration": 14400,
  "chapters": [
    {
      "id": "ch_1",
      "title": "Chapter 1",
      "startTime": 0,
      "duration": 1800
    }
  ],
  "coverImage": "https://...",
  "audioUrl": "https://...",
  "progress": 0.35
}
```
**Source:** `src/store/slices/audiobooksSlice.ts`

---

### POST /api/v1/audiobooks
**Purpose:** Create new audiobook (from upload)  
**Headers:** `Authorization: Bearer {token}`  
**Request Body:**
```json
{
  "title": "My Audiobook",
  "fileId": "upload_456"
}
```
**Response:** 201 Created
```json
{
  "id": "book_789",
  "title": "My Audiobook",
  "status": "processing"
}
```
**Source:** `src/types/audiobook.ts`

---

### PATCH /api/v1/audiobooks/{id}
**Purpose:** Update audiobook metadata  
**Headers:** `Authorization: Bearer {token}`  
**Request Body:**
```json
{
  "title": "Updated Title"
}
```
**Response:** 200 OK
**Source:** `src/types/audiobook.ts`

---

### DELETE /api/v1/audiobooks/{id}
**Purpose:** Delete audiobook from library  
**Headers:** `Authorization: Bearer {token}`  
**Response:** 204 No Content
**Source:** Implied by Permission system

---

## Store & Marketplace

### GET /api/v1/store/catalog
**Purpose:** Get all audiobooks available for purchase  
**Headers:** `Authorization: Bearer {token}`  
**Query Params:** `?genre=fiction&sort=popular&page=1&limit=20`  
**Response:** 200 OK
```json
{
  "books": [
    {
      "id": "store_book_123",
      "title": "The Great Gatsby",
      "author": "F. Scott Fitzgerald",
      "price": 12.99,
      "credits": 1,
      "genre": "Fiction",
      "rating": 4.7,
      "coverImage": "https://..."
    }
  ],
  "total": 500,
  "page": 1
}
```
**Source:** `src/components/layout/Sidebar.tsx`, `src/store/slices/storeSlice.ts`, `src/pages/Store.tsx`

---

### GET /api/v1/store/books/{id}
**Purpose:** Get detailed store book information  
**Headers:** `Authorization: Bearer {token}`  
**Response:** 200 OK
```json
{
  "id": "store_book_123",
  "title": "The Great Gatsby",
  "author": "F. Scott Fitzgerald",
  "narrator": "Jake Gyllenhaal",
  "description": "A story of decadence...",
  "synopsis": "Set in the Jazz Age...",
  "duration": 14400,
  "chapters": [...],
  "price": 12.99,
  "credits": 1,
  "genre": "Fiction",
  "categories": ["Classic", "Bestseller"],
  "rating": 4.7,
  "reviewCount": 234,
  "sampleAudioUrl": "https://...",
  "coverImage": "https://..."
}
```
**Source:** `src/pages/StoreBookDetail.tsx`, `src/store/slices/storeSlice.ts`

---

### GET /api/v1/store/featured
**Purpose:** Get featured audiobooks for store homepage  
**Headers:** `Authorization: Bearer {token}`  
**Response:** 200 OK
```json
{
  "books": [...]
}
```
**Source:** `src/pages/Store.tsx`

---

### GET /api/v1/store/new-releases
**Purpose:** Get newest audiobook releases  
**Headers:** `Authorization: Bearer {token}`  
**Response:** 200 OK
```json
{
  "books": [...]
}
```
**Source:** `src/pages/Store.tsx`

---

### GET /api/v1/store/bestsellers
**Purpose:** Get bestselling audiobooks  
**Headers:** `Authorization: Bearer {token}`  
**Response:** 200 OK
```json
{
  "books": [...]
}
```
**Source:** `src/pages/Store.tsx`

---

### GET /api/v1/store/books/{id}/related
**Purpose:** Get related/recommended audiobooks  
**Headers:** `Authorization: Bearer {token}`  
**Response:** 200 OK
```json
{
  "books": [...]
}
```
**Source:** `src/pages/StoreBookDetail.tsx`

---

### POST /api/v1/store/purchase
**Purpose:** Purchase a store audiobook  
**Headers:** `Authorization: Bearer {token}`  
**Request Body:**
```json
{
  "bookId": "store_book_123",
  "paymentMethod": "credits"
}
```
**Response:** 200 OK
```json
{
  "success": true,
  "audiobookId": "book_789",
  "creditsRemaining": 49
}
```
**Source:** `src/pages/StoreBookDetail.tsx`, `src/store/slices/storeSlice.ts`

---

## Cart & Checkout

### GET /api/v1/cart
**Purpose:** Get user's shopping cart  
**Headers:** `Authorization: Bearer {token}`  
**Response:** 200 OK
```json
{
  "items": [
    {
      "bookId": "store_book_123",
      "title": "The Great Gatsby",
      "price": 12.99,
      "credits": 1,
      "quantity": 1
    }
  ],
  "subtotal": 25.98,
  "tax": 2.08,
  "total": 28.06
}
```
**Source:** `src/pages/Cart.tsx`, `src/store/slices/cartSlice.ts`

---

### POST /api/v1/cart/items
**Purpose:** Add item to cart  
**Headers:** `Authorization: Bearer {token}`  
**Request Body:**
```json
{
  "bookId": "store_book_123",
  "quantity": 1
}
```
**Response:** 201 Created
```json
{
  "item": {...},
  "cartTotal": 28.06
}
```
**Source:** `src/components/cart/AddToCartModal.tsx`

---

### DELETE /api/v1/cart/items/{bookId}
**Purpose:** Remove item from cart  
**Headers:** `Authorization: Bearer {token}`  
**Response:** 204 No Content
**Source:** `src/pages/Checkout.tsx`, `src/pages/Cart.tsx`

---

### PATCH /api/v1/cart/items/{bookId}
**Purpose:** Update cart item quantity  
**Headers:** `Authorization: Bearer {token}`  
**Request Body:**
```json
{
  "quantity": 2
}
```
**Response:** 200 OK
**Source:** `src/pages/Checkout.tsx`, `src/pages/Cart.tsx`

---

### POST /api/v1/cart/sync
**Purpose:** Sync cart across devices  
**Headers:** `Authorization: Bearer {token}`  
**Request Body:**
```json
{
  "items": [...]
}
```
**Response:** 200 OK
**Source:** `src/store/slices/cartSlice.ts`

---

### POST /api/v1/cart/validate
**Purpose:** Validate cart items availability and pricing  
**Headers:** `Authorization: Bearer {token}`  
**Response:** 200 OK
```json
{
  "valid": true,
  "issues": [],
  "updatedPrices": []
}
```
**Source:** `src/store/slices/cartSlice.ts`

---

### DELETE /api/v1/cart
**Purpose:** Clear entire cart  
**Headers:** `Authorization: Bearer {token}`  
**Response:** 204 No Content
**Source:** `src/pages/Cart.tsx`

---

### POST /api/v1/checkout
**Purpose:** Process checkout and complete purchase  
**Headers:** `Authorization: Bearer {token}`  
**Request Body:**
```json
{
  "paymentMethod": "card",
  "paymentIntentId": "pi_123",
  "items": [...]
}
```
**Response:** 200 OK
```json
{
  "success": true,
  "orderId": "order_456",
  "purchasedBooks": [...]
}
```
**Source:** `src/store/slices/cartSlice.ts`, `src/pages/Checkout.tsx`

---

## Publishing & Listings

### POST /api/v1/store/listings
**Purpose:** Create new store listing (publish audiobook)  
**Headers:** `Authorization: Bearer {token}`  
**Permissions:** PUBLISH_AUDIOBOOK  
**Request Body:**
```json
{
  "audiobookId": "book_789",
  "title": "My Great Novel",
  "author": "John Author",
  "narrator": "Jane Narrator",
  "description": "A compelling story...",
  "synopsis": "Short summary...",
  "genre": "Fiction",
  "language": "en",
  "categories": ["Bestseller"],
  "tags": ["mystery", "thriller"],
  "isbn": "978-3-16-148410-0",
  "publishedYear": 2025,
  "price": 14.99,
  "currency": "USD",
  "status": "pending_review"
}
```
**Response:** 201 Created
```json
{
  "id": "listing_123",
  "status": "pending_review",
  "createdAt": "2025-01-20T00:00:00Z"
}
```
**Source:** `src/pages/PublishToStore.tsx`

---

### GET /api/v1/store/listings/my-listings
**Purpose:** Get current user's store listings  
**Headers:** `Authorization: Bearer {token}`  
**Permissions:** PUBLISH_AUDIOBOOK  
**Query Params:** `?status=all&page=1&limit=20`  
**Response:** 200 OK
```json
{
  "listings": [
    {
      "id": "listing_123",
      "title": "My Great Novel",
      "status": "published",
      "price": 14.99,
      "totalSales": 45,
      "rating": 4.5,
      "publishedAt": "2025-01-15T00:00:00Z"
    }
  ],
  "total": 5
}
```
**Source:** `src/pages/MyListings.tsx`

---

### GET /api/v1/store/listings/{id}
**Purpose:** Get specific listing details  
**Headers:** `Authorization: Bearer {token}`  
**Permissions:** PUBLISH_AUDIOBOOK  
**Response:** 200 OK
```json
{
  "id": "listing_123",
  "audiobookId": "book_789",
  "title": "My Great Novel",
  "status": "published",
  "price": 14.99,
  "totalSales": 45,
  "revenue": 674.55,
  "rating": 4.5
}
```
**Source:** `src/pages/PublishToStore.tsx`

---

### PATCH /api/v1/store/listings/{id}
**Purpose:** Update listing information  
**Headers:** `Authorization: Bearer {token}`  
**Permissions:** PUBLISH_AUDIOBOOK  
**Request Body:**
```json
{
  "price": 12.99,
  "description": "Updated description..."
}
```
**Response:** 200 OK
**Source:** `src/pages/PublishToStore.tsx`

---

### DELETE /api/v1/store/listings/{id}
**Purpose:** Delete/unlist a store listing  
**Headers:** `Authorization: Bearer {token}`  
**Permissions:** PUBLISH_AUDIOBOOK  
**Response:** 204 No Content
**Source:** `src/pages/MyListings.tsx`

---

### POST /api/v1/store/listings/{id}/cover
**Purpose:** Upload cover image for listing  
**Headers:** `Authorization: Bearer {token}`  
**Permissions:** PUBLISH_AUDIOBOOK  
**Request:** Multipart form data with image file  
**Response:** 200 OK
```json
{
  "coverImageUrl": "https://cdn.example.com/covers/listing_123.jpg"
}
```
**Source:** `src/pages/PublishToStore.tsx`

---

## Payments & Subscriptions

### GET /api/v1/pricing/plans
**Purpose:** Get available subscription plans  
**Response:** 200 OK
```json
{
  "plans": [
    {
      "id": "premium",
      "name": "Premium",
      "price": 9.99,
      "interval": "month",
      "features": [...]
    }
  ]
}
```
**Source:** `src/pages/Pricing.tsx`

---

### GET /api/v1/pricing/credits
**Purpose:** Get credit packages available for purchase  
**Response:** 200 OK
```json
{
  "packages": [
    {
      "id": "credits_10",
      "credits": 10,
      "price": 9.99,
      "bonus": 0
    }
  ]
}
```
**Source:** `src/pages/Pricing.tsx`

---

### GET /api/v1/pricing/plan/{id}
**Purpose:** Get specific plan details  
**Response:** 200 OK
**Source:** `src/pages/Purchase.tsx`

---

### GET /api/v1/pricing/credits/{id}
**Purpose:** Get specific credit package details  
**Response:** 200 OK
**Source:** `src/pages/Purchase.tsx`

---

### POST /api/v1/payments/create-intent
**Purpose:** Create payment intent for Stripe/payment processor  
**Headers:** `Authorization: Bearer {token}`  
**Request Body:**
```json
{
  "amount": 9.99,
  "currency": "USD",
  "itemType": "credits",
  "itemId": "credits_10"
}
```
**Response:** 200 OK
```json
{
  "clientSecret": "pi_123_secret_456",
  "paymentIntentId": "pi_123"
}
```
**Source:** `src/pages/Purchase.tsx`

---

### POST /api/v1/payments/confirm
**Purpose:** Confirm payment completion  
**Headers:** `Authorization: Bearer {token}`  
**Request Body:**
```json
{
  "paymentIntentId": "pi_123"
}
```
**Response:** 200 OK
```json
{
  "success": true,
  "creditsAdded": 10
}
```
**Source:** `src/pages/Purchase.tsx`

---

### POST /api/v1/subscriptions/create
**Purpose:** Create new subscription  
**Headers:** `Authorization: Bearer {token}`  
**Request Body:**
```json
{
  "planId": "premium",
  "paymentMethodId": "pm_123"
}
```
**Response:** 201 Created
```json
{
  "subscriptionId": "sub_123",
  "status": "active",
  "currentPeriodEnd": "2025-02-20T00:00:00Z"
}
```
**Source:** `src/pages/Purchase.tsx`

---

### POST /api/v1/subscriptions/upgrade
**Purpose:** Upgrade user subscription tier  
**Headers:** `Authorization: Bearer {token}`  
**Request Body:**
```json
{
  "tier": "publisher"
}
```
**Response:** 200 OK
**Source:** `src/constants/permissions.ts`

---

### GET /api/v1/subscriptions/manage
**Purpose:** Get subscription management portal URL  
**Headers:** `Authorization: Bearer {token}`  
**Response:** 200 OK
```json
{
  "url": "https://billing.stripe.com/..."
}
```
**Source:** `src/pages/Checkout.tsx`

---

## Permissions & Access Control

### GET /api/v1/users/me/permissions
**Purpose:** Get current user's permissions and role  
**Headers:** `Authorization: Bearer {token}`  
**Response:** 200 OK
```json
{
  "role": "publisher",
  "tier": "publisher",
  "permissions": [
    "UPLOAD_AUDIOBOOK",
    "PUBLISH_AUDIOBOOK",
    "VIEW_ANALYTICS"
  ],
  "limits": {
    "maxUploads": 500,
    "maxStorage": 500,
    "maxDevices": 10,
    "maxPublishedBooks": 1000
  },
  "isAdmin": false
}
```
**Source:** `src/contexts/PermissionsContext.tsx`

---

### GET /api/v1/users/me/usage
**Purpose:** Get current usage stats against limits  
**Headers:** `Authorization: Bearer {token}`  
**Response:** 200 OK
```json
{
  "uploads": 42,
  "storageUsed": 125.5,
  "devicesConnected": 3,
  "publishedBooks": 15
}
```
**Source:** `src/hooks/usePermissions.ts`

---

### GET /api/v1/permissions/check
**Purpose:** Check if user has specific permission  
**Headers:** `Authorization: Bearer {token}`  
**Query Params:** `?permission=PUBLISH_AUDIOBOOK`  
**Response:** 200 OK
```json
{
  "allowed": true,
  "reason": null
}
```
**Source:** `src/hooks/usePermissions.ts`

---

## Audio Processing & Previews

### POST /api/v1/previews
**Purpose:** Create preview from uploaded PDF  
**Headers:** `Authorization: Bearer {token}`  
**Request:** Multipart form data with PDF file  
**Response:** 201 Created
```json
{
  "previewId": "preview_123",
  "status": "processing"
}
```
**Source:** `src/components/upload/FileUpload.tsx`

---

### GET /api/v1/previews/{previewId}
**Purpose:** Get preview details and status  
**Headers:** `Authorization: Bearer {token}`  
**Response:** 200 OK
```json
{
  "id": "preview_123",
  "status": "completed",
  "title": "Book Title",
  "characters": [
    {
      "name": "John",
      "gender": "male"
    }
  ],
  "sampleAudioUrl": "https://..."
}
```
**Source:** `src/pages/AudiobookPreview.tsx`

---

### GET /api/v1/previews/{previewId}/status
**Purpose:** Get processing status of preview  
**Headers:** `Authorization: Bearer {token}`  
**Response:** 200 OK
```json
{
  "status": "processing",
  "progress": 0.75,
  "estimatedTimeRemaining": 120
}
```
**Source:** `src/components/audiobook/ProcessingStatus.tsx`

---

### GET /api/v1/voices/available
**Purpose:** Get available TTS voices  
**Query Params:** `?gender=all&accent=all&language=en`  
**Response:** 200 OK
```json
{
  "voices": [
    {
      "id": "voice_123",
      "name": "Emma (US)",
      "gender": "female",
      "accent": "american",
      "language": "en",
      "sampleUrl": "https://..."
    }
  ]
}
```
**Source:** `src/components/audiobook/VoiceSelector.tsx`

---

### PUT /api/v1/previews/{previewId}/character-voices
**Purpose:** Assign voices to characters  
**Headers:** `Authorization: Bearer {token}`  
**Request Body:**
```json
{
  "characters": [
    {
      "name": "John",
      "voiceId": "voice_123"
    }
  ]
}
```
**Response:** 200 OK
**Source:** `src/components/audiobook/VoiceSelector.tsx`, `src/pages/AudiobookPreview.tsx`

---

### GET /api/v1/previews/{previewId}/basic-voice-sample
**Purpose:** Get sample audio with basic voice  
**Headers:** `Authorization: Bearer {token}`  
**Response:** 200 OK
```json
{
  "audioUrl": "https://..."
}
```
**Source:** `src/components/audiobook/VoicePreview.tsx`

---

### GET /api/v1/previews/{previewId}/character-samples
**Purpose:** Get sample audio with character voices  
**Headers:** `Authorization: Bearer {token}`  
**Response:** 200 OK
```json
{
  "audioUrl": "https://..."
}
```
**Source:** `src/components/audiobook/VoicePreview.tsx`

---

### POST /api/v1/previews/{previewId}/confirm
**Purpose:** Confirm preview and create full audiobook  
**Headers:** `Authorization: Bearer {token}`  
**Response:** 201 Created
```json
{
  "audiobookId": "book_789",
  "status": "processing"
}
```
**Source:** `src/pages/AudiobookPreview.tsx`

---

## Playback & Progress

### GET /api/v1/audiobooks/{id}/audio
**Purpose:** Get streaming audio URL  
**Headers:** `Authorization: Bearer {token}`  
**Response:** 200 OK
```json
{
  "audioUrl": "https://cdn.example.com/audiobooks/book_123.mp3",
  "format": "mp3",
  "duration": 14400
}
```
**Source:** `src/components/audiobook/AudioPlayer.tsx`

---

### POST /api/v1/audiobooks/{id}/progress
**Purpose:** Save playback position  
**Headers:** `Authorization: Bearer {token}`  
**Request Body:**
```json
{
  "position": 3600,
  "duration": 14400,
  "chapterId": "ch_1"
}
```
**Response:** 200 OK
**Source:** `src/components/audiobook/AudioPlayer.tsx`

---

### GET /api/v1/audiobooks/{id}/progress
**Purpose:** Get saved playback position  
**Headers:** `Authorization: Bearer {token}`  
**Response:** 200 OK
```json
{
  "position": 3600,
  "progress": 0.25,
  "lastPlayedAt": "2025-01-20T14:30:00Z"
}
```
**Source:** `src/components/audiobook/AudioPlayer.tsx`

---

### POST /api/v1/audiobooks/{id}/bookmarks
**Purpose:** Create bookmark  
**Headers:** `Authorization: Bearer {token}`  
**Request Body:**
```json
{
  "position": 1234,
  "note": "Important part"
}
```
**Response:** 201 Created
```json
{
  "id": "bookmark_123",
  "position": 1234,
  "note": "Important part"
}
```
**Source:** `src/components/audiobook/AudioPlayer.tsx`

---

### GET /api/v1/audiobooks/{id}/bookmarks
**Purpose:** Get all bookmarks for audiobook  
**Headers:** `Authorization: Bearer {token}`  
**Response:** 200 OK
```json
{
  "bookmarks": [
    {
      "id": "bookmark_123",
      "position": 1234,
      "note": "Important part",
      "createdAt": "2025-01-20T00:00:00Z"
    }
  ]
}
```
**Source:** `src/components/audiobook/AudioPlayer.tsx`

---

### GET /api/v1/audiobooks/{id}/chapters
**Purpose:** Get chapter information  
**Headers:** `Authorization: Bearer {token}`  
**Response:** 200 OK
```json
{
  "chapters": [
    {
      "id": "ch_1",
      "title": "Chapter 1",
      "startTime": 0,
      "duration": 1800
    }
  ]
}
```
**Source:** `src/components/audiobook/AudioPlayer.tsx`

---

### POST /api/v1/audiobooks/{id}/complete
**Purpose:** Mark audiobook as completed  
**Headers:** `Authorization: Bearer {token}`  
**Response:** 200 OK
**Source:** `src/components/audiobook/AudioPlayer.tsx`

---

## Search & Discovery

### GET /api/v1/search
**Purpose:** Search audiobooks across library and store  
**Headers:** `Authorization: Bearer {token}`  
**Query Params:** `?q=gatsby&scope=all&limit=20`  
**Response:** 200 OK
```json
{
  "results": [
    {
      "id": "book_123",
      "title": "The Great Gatsby",
      "author": "F. Scott Fitzgerald",
      "type": "library"
    }
  ],
  "total": 5
}
```
**Source:** `src/components/layout/Navbar.tsx`

---

### GET /api/v1/recommendations
**Purpose:** Get personalized audiobook recommendations  
**Headers:** `Authorization: Bearer {token}`  
**Response:** 200 OK
```json
{
  "recommendations": [
    {
      "id": "book_456",
      "title": "To Kill a Mockingbird",
      "reason": "Based on your interest in classics"
    }
  ]
}
```
**Source:** `src/pages/Dashboard.tsx`

---

## Notifications

### GET /api/v1/notifications
**Purpose:** Get user notifications  
**Headers:** `Authorization: Bearer {token}`  
**Query Params:** `?unread=true&limit=10`  
**Response:** 200 OK
```json
{
  "notifications": [
    {
      "id": "notif_123",
      "type": "purchase_complete",
      "title": "Purchase Complete",
      "message": "Your audiobook is ready",
      "read": false,
      "createdAt": "2025-01-20T10:00:00Z"
    }
  ],
  "unreadCount": 3
}
```
**Source:** `src/components/layout/Navbar.tsx`

---

### PATCH /api/v1/notifications/{id}/read
**Purpose:** Mark notification as read  
**Headers:** `Authorization: Bearer {token}`  
**Response:** 200 OK
**Source:** `src/components/layout/Navbar.tsx`

---

### POST /api/v1/notifications/mark-all-read
**Purpose:** Mark all notifications as read  
**Headers:** `Authorization: Bearer {token}`  
**Response:** 200 OK
**Source:** `src/components/layout/Navbar.tsx`

---

## Analytics (Publisher/Admin)

### GET /api/v1/analytics/sales
**Purpose:** Get sales analytics for publisher  
**Headers:** `Authorization: Bearer {token}`  
**Permissions:** VIEW_ANALYTICS  
**Query Params:** `?period=month&listingId=listing_123`  
**Response:** 200 OK
```json
{
  "totalSales": 245,
  "totalRevenue": 3182.55,
  "salesByDay": [...],
  "topBooks": [...]
}
```
**Source:** Publisher dashboard (implied by permissions)

---

### GET /api/v1/analytics/listeners
**Purpose:** Get listener demographics and behavior  
**Headers:** `Authorization: Bearer {token}`  
**Permissions:** VIEW_ANALYTICS  
**Response:** 200 OK
```json
{
  "totalListeners": 189,
  "avgCompletionRate": 0.78,
  "demographics": {...}
}
```
**Source:** Publisher analytics (implied)

---

### GET /api/v1/analytics/all
**Purpose:** Get system-wide analytics (Admin only)  
**Headers:** `Authorization: Bearer {token}`  
**Permissions:** VIEW_ALL_ANALYTICS  
**Response:** 200 OK
```json
{
  "totalUsers": 10523,
  "totalAudiobooks": 8934,
  "totalRevenue": 125340.50
}
```
**Source:** Admin dashboard (implied)

---

## Admin Endpoints

### GET /api/v1/admin/users
**Purpose:** Get all users (Admin only)  
**Headers:** `Authorization: Bearer {token}`  
**Permissions:** MANAGE_USERS  
**Query Params:** `?page=1&limit=50&role=all`  
**Response:** 200 OK
```json
{
  "users": [...],
  "total": 10523
}
```
**Source:** Admin panel (implied by permissions)

---

### PATCH /api/v1/admin/users/{userId}
**Purpose:** Update user (Admin only)  
**Headers:** `Authorization: Bearer {token}`  
**Permissions:** MANAGE_USERS  
**Request Body:**
```json
{
  "role": "publisher",
  "status": "active"
}
```
**Response:** 200 OK
**Source:** Admin panel (implied)

---

### DELETE /api/v1/admin/users/{userId}
**Purpose:** Delete user (Admin only)  
**Headers:** `Authorization: Bearer {token}`  
**Permissions:** MANAGE_USERS  
**Response:** 204 No Content
**Source:** Admin panel (implied)

---

### GET /api/v1/admin/content
**Purpose:** Get all content for moderation (Admin only)  
**Headers:** `Authorization: Bearer {token}`  
**Permissions:** MANAGE_CONTENT, MODERATION  
**Response:** 200 OK
**Source:** Admin panel (implied)

---

### PATCH /api/v1/admin/listings/{id}/status
**Purpose:** Approve/reject store listings (Admin only)  
**Headers:** `Authorization: Bearer {token}`  
**Permissions:** MODERATION  
**Request Body:**
```json
{
  "status": "published",
  "feedback": "Looks great!"
}
```
**Response:** 200 OK
**Source:** Admin moderation panel (implied)

---

## Summary Statistics

**Total Endpoints:** 100+

**By Category:**
- Authentication & Authorization: 6
- User Management: 10
- Audiobook Library: 5
- Store & Marketplace: 8
- Cart & Checkout: 9
- Publishing & Listings: 7
- Payments & Subscriptions: 10
- Permissions & Access Control: 3
- Audio Processing & Previews: 10
- Playback & Progress: 8
- Search & Discovery: 2
- Notifications: 3
- Analytics: 3
- Admin: 5

**Authentication Required:** All endpoints except:
- POST /api/v1/auth/signup
- POST /api/v1/auth/login
- POST /api/v1/auth/forgot-password
- GET /api/v1/pricing/plans
- GET /api/v1/pricing/credits
- GET /api/v1/voices/available

**Permission-Gated Endpoints:**
- All `/api/v1/store/listings/*` require PUBLISH_AUDIOBOOK
- All `/api/v1/analytics/*` require VIEW_ANALYTICS or VIEW_ALL_ANALYTICS
- All `/api/v1/admin/*` require specific admin permissions

---

## Implementation Notes

### Headers
All authenticated endpoints should include:
```
Authorization: Bearer {jwt_token}
Content-Type: application/json
```

### Error Responses
Standard error format:
```json
{
  "error": {
    "code": "UNAUTHORIZED",
    "message": "Invalid or expired token",
    "details": {}
  }
}
```

### Pagination
Standard pagination parameters:
- `page`: Page number (1-indexed)
- `limit`: Items per page (default: 20, max: 100)
- `sort`: Sort field and direction (e.g., `created_at:desc`)


### WebSocket Endpoints (Future)
 WebSocket for real-time features:
- `ws://api/v1/audiobook/{id}/sync` - Real-time playback sync
- `ws://api/v1/notifications` - Real-time notifications
- `ws://api/v1/previews/{id}/status` - Real-time processing updates
