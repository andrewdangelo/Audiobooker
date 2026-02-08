"""
MongoDB Collection Schemas

These are data models representing the structure of documents in MongoDB collections.
MongoDB is schema-less, but we define these for validation and documentation.
"""
__author__ = "Mohammad Saifan"

from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field


# Collection names as constants
class Collections:
    USER_DATA = "user_data"
    AUTH_SERVICE_USER_DATA = "users"
    USER_PREFERENCES = "user_preferences"
    USER_CREDITS = "user_credits"
    USER_STATS = "user_stats"
    BOOKS = "books"
    CHAPTERS = "chapters"
    USER_LIBRARY = "user_library"
    USER_ACTIVITY = "user_activity"
    CART_ITEMS = "cart_items"
    STORE_LISTINGS = "store_listings"
    BOOKMARKS = "bookmarks"
    NOTIFICATIONS = "notifications"


class UserDataModel(BaseModel):
    """User Data document model"""
    id: str
    email: str
    name: Optional[str] = None
    avatar_url: Optional[str] = None
    role: str = "free"  # free, premium, publisher, admin
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class UserPreferencesModel(BaseModel):
    """User Preferences document model"""
    id: str
    user_id: str
    email_notifications: bool = True
    marketing_emails: bool = False
    theme: str = "light"  # light, dark
    language: str = "en"
    autoplay: bool = True
    playback_speed: float = 1.0
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class UserCreditsModel(BaseModel):
    """User Credits document model"""
    id: str
    user_id: str
    credits: int = 0
    credits_used: int = 0
    credits_expiring: int = 0
    expiry_date: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class UserStatsModel(BaseModel):
    """User Statistics document model"""
    id: str
    user_id: str
    total_books: int = 0
    hours_listened: float = 0.0
    books_completed: int = 0
    favorite_genre: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class ChapterModel(BaseModel):
    """Chapter document model"""
    id: str
    title: str
    start_time: int  # in seconds
    duration: int  # in seconds
    chapter_number: int


class BookModel(BaseModel):
    """Book document model"""
    id: str
    title: str
    author: str
    narrator: Optional[str] = None
    description: Optional[str] = None
    synopsis: Optional[str] = None
    duration: int  # in seconds
    cover_image_url: Optional[str] = None
    audio_url: Optional[str] = None
    sample_audio_url: Optional[str] = None
    genre: Optional[str] = None
    categories: Optional[List[str]] = None
    rating: float = 0.0
    review_count: int = 0
    price: Optional[float] = None
    credits_required: int = 1
    is_store_item: bool = False
    chapters: Optional[List[ChapterModel]] = []
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class UserLibraryModel(BaseModel):
    """User Library document model"""
    id: str
    user_id: str
    book_id: str
    progress: float = 0.0  # 0.0 to 1.0
    last_played_at: Optional[datetime] = None
    added_at: datetime = Field(default_factory=datetime.utcnow)
    completed: bool = False


class UserActivityModel(BaseModel):
    """User Activity document model"""
    id: str
    user_id: str
    activity_type: str  # completed, started, purchased, etc.
    book_id: Optional[str] = None
    title: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    meta_data: Optional[Dict[str, Any]] = None


class CartItemModel(BaseModel):
    """Shopping cart item document model"""
    id: str
    user_id: str
    book_id: str
    quantity: int = 1
    created_at: datetime = Field(default_factory=datetime.utcnow)


class StoreListingModel(BaseModel):
    """Store listing document model"""
    id: str
    user_id: str
    book_id: str
    title: str
    price: Optional[float] = None
    status: str = "pending_review"  # pending_review, published, rejected
    total_sales: int = 0
    revenue: float = 0.0
    rating: float = 0.0
    description: Optional[str] = None
    cover_image_url: Optional[str] = None
    admin_feedback: Optional[str] = None
    published_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class BookmarkModel(BaseModel):
    """Bookmark document model"""
    id: str
    user_id: str
    book_id: str
    position: int  # Position in seconds
    note: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class NotificationModel(BaseModel):
    """Notification document model"""
    id: str
    user_id: str
    notification_type: str  # purchase_complete, new_release, etc.
    title: str
    message: str
    read: bool = False
    meta_data: Optional[Dict[str, Any]] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)