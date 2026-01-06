/**
 * Store Listing Types
 * 
 * Type definitions for publishing audiobooks to the store.
 * 
 * @author Andrew D'Angelo
 */

export interface StoreListing {
  id: string;
  audiobookId: string; // Reference to the uploaded audiobook
  
  // Basic Information
  title: string;
  author: string;
  narrator?: string;
  publisher?: string;
  
  // Content Details
  description: string;
  synopsis: string;
  language: string;
  duration: number; // in seconds
  
  // Categorization
  genre: string;
  categories: string[];
  tags: string[];
  
  // Publishing Details
  isbn?: string;
  publishedYear: number;
  edition?: string;
  
  // Media
  coverImageUrl?: string;
  sampleAudioUrl?: string;
  
  // Pricing
  price: number; // in USD
  currency: string;
  discountPrice?: number;
  isFree: boolean;
  
  // Visibility & Status
  status: 'draft' | 'pending_review' | 'published' | 'unlisted' | 'rejected';
  isPublic: boolean;
  publishedAt?: string;
  
  // Metadata
  createdBy: string; // User ID
  createdAt: string;
  updatedAt: string;
  
  // Sales & Analytics
  totalSales?: number;
  rating?: number;
  reviewCount?: number;
}

export interface StoreListingCreate {
  audiobookId: string;
  
  // Required fields
  title: string;
  author: string;
  description: string;
  synopsis: string;
  genre: string;
  price: number;
  
  // Optional fields
  narrator?: string;
  publisher?: string;
  language?: string;
  categories?: string[];
  tags?: string[];
  isbn?: string;
  publishedYear?: number;
  edition?: string;
  coverImageUrl?: string;
  sampleAudioUrl?: string;
  currency?: string;
  discountPrice?: number;
  isFree?: boolean;
}

export interface StoreListingUpdate {
  title?: string;
  author?: string;
  narrator?: string;
  publisher?: string;
  description?: string;
  synopsis?: string;
  language?: string;
  genre?: string;
  categories?: string[];
  tags?: string[];
  isbn?: string;
  publishedYear?: number;
  edition?: string;
  coverImageUrl?: string;
  sampleAudioUrl?: string;
  price?: number;
  currency?: string;
  discountPrice?: number;
  isFree?: boolean;
  status?: StoreListing['status'];
  isPublic?: boolean;
}

// Genre options
export const GENRE_OPTIONS = [
  'Fiction',
  'Non-Fiction',
  'Mystery & Thriller',
  'Science Fiction & Fantasy',
  'Romance',
  'Biography & Memoir',
  'Self-Help',
  'Business & Economics',
  'History',
  'Science & Technology',
  'Children & Young Adult',
  'Poetry',
  'Philosophy',
  'Religion & Spirituality',
  'Horror',
  'Crime & Detective',
  'Humor',
  'Travel',
  'Cooking & Food',
  'Health & Wellness',
  'Other',
] as const;

// Language options
export const LANGUAGE_OPTIONS = [
  { value: 'en', label: 'English' },
  { value: 'es', label: 'Spanish' },
  { value: 'fr', label: 'French' },
  { value: 'de', label: 'German' },
  { value: 'it', label: 'Italian' },
  { value: 'pt', label: 'Portuguese' },
  { value: 'zh', label: 'Chinese' },
  { value: 'ja', label: 'Japanese' },
  { value: 'ko', label: 'Korean' },
  { value: 'ru', label: 'Russian' },
] as const;

// Category options
export const CATEGORY_OPTIONS = [
  'Bestseller',
  'New Release',
  'Award Winner',
  'Classic',
  'Educational',
  'Professional',
  'Entertainment',
  'Motivational',
  'Anthology',
  'Series',
] as const;
