/**
 * AudiobookCard Component
 * 
 * Displays a single audiobook card with cover art, title, author, and duration.
 * Clicking the card navigates to the book detail page.
 */

import { Link } from 'react-router-dom'
import { Card, CardContent } from '../ui/card'
import { Clock, User, Crown, Sparkles, Radio } from 'lucide-react'
import { formatDuration } from '@/data/demoBooks'
import { Progress } from '../ui/progress'
import type { AudiobookConversion } from '@/store/slices/audiobooksSlice'

interface AudiobookCardProps {
  id: string
  title: string
  author: string
  duration: number // in seconds
  coverImage?: string
  genre?: string
  isPremium?: boolean
  purchaseType?: 'basic' | 'premium'
  status?: 'draft' | 'processing' | 'completed' | 'failed'
  conversion?: AudiobookConversion | null
}

export default function AudiobookCard({ 
  id, 
  title, 
  author, 
  duration, 
  coverImage,
  genre,
  isPremium,
  purchaseType,
  status,
  conversion,
}: AudiobookCardProps) {
  const isDraft = Boolean(conversion) && status === 'draft'
  const isConverting = Boolean(conversion) && status === 'processing'

  return (
    <Link to={`/book/${id}`}>
      <Card className={`overflow-hidden hover:shadow-lg transition-all duration-300 hover:scale-[1.02] cursor-pointer group${
        isPremium ? ' ring-2 ring-amber-400/60 hover:ring-amber-400' : ''
      }`}>
        {/* Cover Image */}
        <div className="aspect-[3/4] relative overflow-hidden bg-gradient-to-br from-primary/20 to-primary/40">
          {coverImage ? (
            <img
              src={coverImage}
              alt={title}
              className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
            />
          ) : (
            <div className="w-full h-full flex items-center justify-center">
              <svg
                className="w-20 h-20 text-primary/60"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={1.5}
                  d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253"
                />
              </svg>
            </div>
          )}
          
          {/* Genre Badge */}
          {genre && (
            <div className="absolute top-2 left-2">
              <span className="px-2 py-1 text-xs font-medium bg-background/90 backdrop-blur-sm rounded-full">
                {genre}
              </span>
            </div>
          )}

          {/* Premium Badge */}
          {isPremium && (
            <div className="absolute top-2 right-2">
              <span className="inline-flex items-center gap-1 px-2 py-1 text-xs font-semibold bg-amber-500 text-white rounded-full shadow">
                <Crown className="h-3 w-3" />
                {purchaseType === 'premium' ? 'Theatrical' : 'Premium'}
              </span>
            </div>
          )}

          {(isDraft || isConverting) && (
            <div className="absolute inset-x-2 bottom-2 rounded-2xl bg-background/95 p-2 shadow-lg backdrop-blur">
              <div className="mb-1 flex items-center justify-between gap-2 text-[11px] font-medium">
                <span className="inline-flex items-center gap-1">
                  {isDraft ? <Sparkles className="h-3 w-3 text-primary" /> : <Radio className="h-3 w-3 text-primary" />}
                  {isDraft ? 'Needs setup' : 'Converting'}
                </span>
                <span className="text-muted-foreground">
                  {isDraft ? 'Review metadata' : `${conversion?.progress ?? 0}%`}
                </span>
              </div>
              <Progress value={isDraft ? 8 : conversion?.progress ?? 0} className="h-1.5" />
            </div>
          )}
        </div>
        
        {/* Card Content */}
        <CardContent className="p-4">
          <h3 className="font-semibold text-lg leading-tight mb-1 line-clamp-2 group-hover:text-primary transition-colors">
            {title}
          </h3>
          
          <div className="flex items-center gap-1 text-sm text-muted-foreground mb-2">
            <User className="h-3 w-3" />
            <span className="truncate">{author}</span>
          </div>
          
          {conversion ? (
            <div className="space-y-1">
              <div className="flex items-center gap-1 text-sm text-muted-foreground">
                <Clock className="h-3 w-3" />
                <span>{conversion.etaLabel}</span>
              </div>
              <p className="text-xs text-muted-foreground line-clamp-2">
                {conversion.currentStep}
              </p>
            </div>
          ) : (
            <div className="flex items-center gap-1 text-sm text-muted-foreground">
              <Clock className="h-3 w-3" />
              <span>{formatDuration(duration)}</span>
            </div>
          )}
        </CardContent>
      </Card>
    </Link>
  )
}
