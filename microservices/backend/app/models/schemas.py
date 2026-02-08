"""
Pydantic Models and Schemas

Request/Response models for API endpoints.
"""
__author__ = "Mohammad Saifan"

from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List
from datetime import datetime


# ============== Health ==============

class HealthResponse(BaseModel):
    """Health check response"""
    
    status: str = Field(..., description="Service health status")
    service: str = Field(..., description="Service name")
    timestamp: str = Field(..., description="Current timestamp")
    version: str = Field(..., description="Service version")


# ============== User Management ==============

class UserProfileResponse(BaseModel):
    """User profile response"""
    
    _id: str
    email: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    hashed_password: Optional[str] = None
    is_active: Optional[bool] = None
    is_verified: Optional[bool] = None
    auth_provider: Optional[str] = None
    avatar_url: Optional[str] = None
    role: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    last_login: Optional[str] = None
    
    class Config:
        from_attributes = True


class UserProfileUpdate(BaseModel):
    """User profile update request"""
    
    name: Optional[str] = None
    email: Optional[EmailStr] = None


class AvatarUploadResponse(BaseModel):
    """Avatar upload response"""
    
    avatar_url: str


class UserPreferencesResponse(BaseModel):
    """User preferences response"""
    
    email_notifications: bool
    marketing_emails: bool
    theme: str
    language: str
    autoplay: bool
    playback_speed: float
    
    class Config:
        from_attributes = True


class UserPreferencesUpdate(BaseModel):
    """User preferences update request"""
    
    email_notifications: Optional[bool] = None
    marketing_emails: Optional[bool] = None
    theme: Optional[str] = None
    language: Optional[str] = None
    autoplay: Optional[bool] = None
    playback_speed: Optional[float] = None


class UserCreditsResponse(BaseModel):
    """User credits response"""
    
    credits: int
    credits_used: int
    credits_expiring: int
    expiry_date: Optional[str] = None
    
    class Config:
        from_attributes = True


class UserStatsResponse(BaseModel):
    """User statistics response"""
    
    total_books: int
    hours_listened: float
    books_completed: int
    favorite_genre: Optional[str] = None
    
    class Config:
        from_attributes = True


class ActivityItem(BaseModel):
    """Single activity item"""
    
    user_id: str
    type: str
    title: Optional[str] = None
    timestamp: str
    book_id: Optional[str] = None


class UserActivityResponse(BaseModel):
    """User activity response"""
    
    activities: List[ActivityItem]


class UserSettingsResponse(BaseModel):
    """User settings response"""
    
    theme: str
    language: str
    autoplay: bool
    playback_speed: float


# ============== Books ==============

class ChapterInfo(BaseModel):
    """Chapter information"""
    
    id: str
    title: str
    start_time: int
    duration: int
    chapter_number: int
    
    class Config:
        from_attributes = True


class BookBasic(BaseModel):
    """Basic book information"""
    
    id: str
    title: str
    author: str
    duration: int
    cover_image_url: Optional[str] = None
    progress: Optional[float] = 0.0
    
    class Config:
        from_attributes = True


class BookDetailed(BaseModel):
    """Detailed book information"""
    
    id: str
    title: str
    author: str
    narrator: Optional[str] = None
    duration: int
    chapters: List[ChapterInfo]
    cover_image_url: Optional[str] = None
    audio_url: Optional[str] = None
    progress: Optional[float] = 0.0
    description: Optional[str] = None
    
    class Config:
        from_attributes = True


class BookListResponse(BaseModel):
    """Paginated book list response"""
    
    books: List[BookBasic]
    total: int
    page: int
    pages: int


class BookCreateRequest(BaseModel):
    """Create book request"""
    
    title: str
    file_id: str


class BookUpdateRequest(BaseModel):
    """Update book metadata request"""
    
    title: Optional[str] = None
    author: Optional[str] = None
    narrator: Optional[str] = None
    description: Optional[str] = None


class ContinueListeningItem(BaseModel):
    """Continue listening item"""
    
    id: str
    title: str
    progress: float
    last_played_at: str
    
    class Config:
        from_attributes = True


class ContinueListeningResponse(BaseModel):
    """Continue listening response"""
    
    books: List[ContinueListeningItem]


class BookshelfItem(BaseModel):
    """Bookshelf item"""
    
    id: str
    title: str
    added_at: str
    
    class Config:
        from_attributes = True


class BookshelfResponse(BaseModel):
    """Bookshelf response"""
    
    books: List[BookshelfItem]


# ============== Store ==============

class StoreBookBasic(BaseModel):
    """Basic store book information"""
    
    id: str
    title: str
    author: str
    price: Optional[float] = None
    credits: int
    genre: Optional[str] = None
    rating: float
    cover_image_url: Optional[str] = None
    
    class Config:
        from_attributes = True


class StoreCatalogResponse(BaseModel):
    """Store catalog response"""
    
    books: List[StoreBookBasic]
    total: int
    page: int

class PurchaseResponse(BaseModel):
    """Purchase response"""
    
    book_id: str
    payment_method: str
    
    class Config:    
        from_attributes = True

class StoreBookDetailed(BaseModel):
    """Detailed store book information"""
    
    id: str
    title: str
    author: str
    narrator: Optional[str] = None
    description: Optional[str] = None
    synopsis: Optional[str] = None
    duration: int
    chapters: List[ChapterInfo]
    price: Optional[float] = None
    credits: int
    genre: Optional[str] = None
    categories: Optional[List[str]] = None
    rating: float
    review_count: int
    sample_audio_url: Optional[str] = None
    cover_image_url: Optional[str] = None
    
    class Config:
        from_attributes = True
        
        
# ============== Cart & Checkout ==============

class CartItemResponse(BaseModel):
    """Cart item response"""
    
    book_id: str
    title: str
    price: Optional[float] = None
    credits: int
    quantity: int
    cover_image: Optional[str] = None


class CartResponse(BaseModel):
    """Shopping cart response"""
    
    items: List[CartItemResponse]
    subtotal: float
    tax: float
    total: float


class AddToCartRequest(BaseModel):
    """Add item to cart request"""
    
    book_id: str = Field(..., alias="bookId")
    quantity: int = 1
    
    class Config:
        populate_by_name = True


class UpdateCartItemRequest(BaseModel):
    """Update cart item request"""
    
    quantity: int = Field(..., ge=1, le=99)


class CartSyncRequest(BaseModel):
    """Cart sync request"""
    
    items: List[dict]


class CartValidationResponse(BaseModel):
    """Cart validation response"""
    
    valid: bool
    issues: List[str]
    updated_prices: List[dict]


class CheckoutRequest(BaseModel):
    """Checkout request"""
    
    payment_method: str = Field(..., alias="paymentMethod")
    payment_intent_id: Optional[str] = Field(None, alias="paymentIntentId")
    items: Optional[List[dict]] = None
    
    class Config:
        populate_by_name = True


class CheckoutResponse(BaseModel):
    """Checkout response"""
    
    success: bool
    order_id: str = Field(..., alias="orderId")
    message: str
    
    class Config:
        populate_by_name = True


# ============== Publishing & Listings ==============

class CreateListingRequest(BaseModel):
    """Create listing request"""
    
    audiobook_id: str = Field(..., alias="audiobookId")
    title: str
    author: str
    narrator: Optional[str] = None
    description: Optional[str] = None
    synopsis: Optional[str] = None
    genre: Optional[str] = None
    language: str = "en"
    categories: Optional[List[str]] = None
    tags: Optional[List[str]] = None
    isbn: Optional[str] = None
    published_year: Optional[int] = Field(None, alias="publishedYear")
    price: float
    currency: str = "USD"
    status: str = "pending_review"
    
    class Config:
        populate_by_name = True


class ListingBasic(BaseModel):
    """Basic listing information"""
    
    id: str
    title: str
    status: str
    price: float
    total_sales: int = Field(0, alias="totalSales")
    rating: float = 0.0
    published_at: Optional[str] = Field(None, alias="publishedAt")
    
    class Config:
        populate_by_name = True
        from_attributes = True


class MyListingsResponse(BaseModel):
    """My listings response"""
    
    listings: List[ListingBasic]
    total: int
    page: int
    pages: int


class ListingDetailed(BaseModel):
    """Detailed listing information"""
    
    id: str
    audiobook_id: str = Field(..., alias="audiobookId")
    title: str
    status: str
    price: float
    total_sales: int = Field(0, alias="totalSales")
    revenue: float = 0.0
    rating: float = 0.0
    
    class Config:
        populate_by_name = True


class UpdateListingRequest(BaseModel):
    """Update listing request"""
    
    price: Optional[float] = None
    description: Optional[str] = None
    title: Optional[str] = None


class CoverUploadResponse(BaseModel):
    """Cover upload response"""
    
    cover_image_url: str = Field(..., alias="coverImageUrl")
    
    class Config:
        populate_by_name = True


# ============== Payments & Subscriptions ==============

class PricingPlan(BaseModel):
    """Pricing plan"""
    
    id: str
    name: str
    price: float
    interval: str
    features: List[str]


class PricingPlansResponse(BaseModel):
    """Pricing plans response"""
    
    plans: List[PricingPlan]


class CreditPackage(BaseModel):
    """Credit package"""
    
    id: str
    credits: int
    price: float
    bonus: int = 0


class CreditPackagesResponse(BaseModel):
    """Credit packages response"""
    
    packages: List[CreditPackage]


class CreatePaymentIntentRequest(BaseModel):
    """Create payment intent request"""
    
    amount: float
    currency: str = "USD"
    item_type: str = Field(..., alias="itemType")
    item_id: str = Field(..., alias="itemId")
    
    class Config:
        populate_by_name = True


class PaymentIntentResponse(BaseModel):
    """Payment intent response"""
    
    payment_intent_id: str = Field(..., alias="paymentIntentId")
    client_secret: str = Field(..., alias="clientSecret")
    amount: float
    currency: str
    
    class Config:
        populate_by_name = True


class ConfirmPaymentRequest(BaseModel):
    """Confirm payment request"""
    
    payment_intent_id: str = Field(..., alias="paymentIntentId")
    
    class Config:
        populate_by_name = True


class PaymentConfirmationResponse(BaseModel):
    """Payment confirmation response"""
    
    success: bool
    payment_intent_id: str = Field(..., alias="paymentIntentId")
    status: str
    
    class Config:
        populate_by_name = True


class CreateSubscriptionRequest(BaseModel):
    """Create subscription request"""
    
    plan_id: str = Field(..., alias="planId")
    payment_method_id: str = Field(..., alias="paymentMethodId")
    
    class Config:
        populate_by_name = True


class SubscriptionResponse(BaseModel):
    """Subscription response"""
    
    subscription_id: str = Field(..., alias="subscriptionId")
    status: str
    plan: str
    
    class Config:
        populate_by_name = True


class UpgradeSubscriptionRequest(BaseModel):
    """Upgrade subscription request"""
    
    tier: str


class SubscriptionPortalResponse(BaseModel):
    """Subscription portal response"""
    
    url: str


# ============== Permissions & Access Control ==============

class UserPermissionsResponse(BaseModel):
    """User permissions response"""
    
    role: str
    tier: str
    permissions: List[str]
    limits: dict
    is_admin: bool = Field(..., alias="isAdmin")
    
    class Config:
        populate_by_name = True


class UserUsageResponse(BaseModel):
    """User usage response"""
    
    uploads: int
    storage_used: float = Field(..., alias="storageUsed")
    devices_connected: int = Field(..., alias="devicesConnected")
    published_books: int = Field(..., alias="publishedBooks")
    
    class Config:
        populate_by_name = True


class PermissionCheckResponse(BaseModel):
    """Permission check response"""
    
    allowed: bool
    reason: Optional[str] = None


# ============== Playback & Progress ==============

class AudioUrlResponse(BaseModel):
    """Audio URL response"""
    
    audio_url: str = Field(..., alias="audioUrl")
    format: str
    duration: int
    
    class Config:
        populate_by_name = True


class SaveProgressRequest(BaseModel):
    """Save progress request"""
    
    position: int
    duration: int
    chapter_id: Optional[str] = Field(None, alias="chapterId")
    
    class Config:
        populate_by_name = True


class ProgressResponse(BaseModel):
    """Progress response"""
    
    position: int
    progress: float
    last_played_at: Optional[str] = Field(None, alias="lastPlayedAt")
    
    class Config:
        populate_by_name = True


class CreateBookmarkRequest(BaseModel):
    """Create bookmark request"""
    
    position: int
    note: Optional[str] = ""


class BookmarkResponse(BaseModel):
    """Bookmark response"""
    
    id: str
    position: int
    note: Optional[str] = None
    created_at: str = Field(..., alias="createdAt")
    
    class Config:
        populate_by_name = True


class BookmarksResponse(BaseModel):
    """Bookmarks response"""
    
    bookmarks: List[BookmarkResponse]


class ChaptersResponse(BaseModel):
    """Chapters response"""
    
    chapters: List[ChapterInfo]


# ============== Search & Discovery ==============

class SearchResult(BaseModel):
    """Single search result"""
    
    id: str
    title: str
    author: str
    type: str  # "library" or "store"
    cover_image: Optional[str] = Field(None, alias="coverImage")
    
    class Config:
        populate_by_name = True


class SearchResponse(BaseModel):
    """Search response"""
    
    results: List[SearchResult]
    total: int


class Recommendation(BaseModel):
    """Recommendation item"""
    
    id: str
    title: str
    author: str
    cover_image: Optional[str] = Field(None, alias="coverImage")
    reason: str
    
    class Config:
        populate_by_name = True


class RecommendationsResponse(BaseModel):
    """Recommendations response"""
    
    recommendations: List[Recommendation]


# ============== Notifications ==============

class NotificationItem(BaseModel):
    """Notification item"""
    
    id: str
    type: str
    title: str
    message: str
    read: bool
    created_at: str = Field(..., alias="createdAt")
    
    class Config:
        populate_by_name = True


class NotificationsResponse(BaseModel):
    """Notifications response"""
    
    notifications: List[NotificationItem]
    unread_count: int = Field(..., alias="unreadCount")
    
    class Config:
        populate_by_name = True


# ============== Analytics ==============

class SalesDataPoint(BaseModel):
    """Sales data point"""
    
    date: str
    sales: int
    revenue: float


class TopBook(BaseModel):
    """Top book data"""
    
    title: str
    sales: int
    revenue: float


class SalesAnalyticsResponse(BaseModel):
    """Sales analytics response"""
    
    total_sales: int = Field(..., alias="totalSales")
    total_revenue: float = Field(..., alias="totalRevenue")
    sales_by_day: List[SalesDataPoint] = Field(..., alias="salesByDay")
    top_books: List[TopBook] = Field(..., alias="topBooks")
    
    class Config:
        populate_by_name = True


class ListenerAnalyticsResponse(BaseModel):
    """Listener analytics response"""
    
    total_listeners: int = Field(..., alias="totalListeners")
    avg_completion_rate: float = Field(..., alias="avgCompletionRate")
    demographics: dict
    
    class Config:
        populate_by_name = True


class SystemAnalyticsResponse(BaseModel):
    """System-wide analytics response"""
    
    total_users: int = Field(..., alias="totalUsers")
    total_audiobooks: int = Field(..., alias="totalAudiobooks")
    total_revenue: float = Field(..., alias="totalRevenue")
    
    class Config:
        populate_by_name = True


# ============== Admin ==============

class AdminUserBasic(BaseModel):
    """Basic user info for admin"""
    
    id: str
    email: str
    name: Optional[str] = None
    role: str
    created_at: str = Field(..., alias="createdAt")
    
    class Config:
        populate_by_name = True


class AdminUsersResponse(BaseModel):
    """Admin users list response"""
    
    users: List[AdminUserBasic]
    total: int
    page: int
    pages: int


class UpdateUserRequest(BaseModel):
    """Update user request (admin)"""
    
    role: Optional[str] = None
    status: Optional[str] = None


class ContentItem(BaseModel):
    """Content item for moderation"""
    
    id: str
    title: str
    user_id: str = Field(..., alias="userId")
    status: str
    created_at: str = Field(..., alias="createdAt")
    
    class Config:
        populate_by_name = True


class ContentModerationResponse(BaseModel):
    """Content moderation response"""
    
    content: List[ContentItem]
    total: int


class UpdateListingStatusRequest(BaseModel):
    """Update listing status request"""
    
    status: str
    feedback: Optional[str] = ""