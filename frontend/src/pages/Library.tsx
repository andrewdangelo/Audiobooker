/**
 * Library Page
 * 
 * Displays the user's audiobook library with search, filter, and tier
 * segregation between basic and premium (theatrical) audiobooks.
 * 
 * @author Andrew D'Angelo
 */

import { useEffect, useState } from 'react'
import { Search, Filter, SortAsc, Crown, BookOpen, Gem } from 'lucide-react'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import AudiobookList from '../components/audiobook/AudiobookList'
import { 
  useAppDispatch, 
  useAppSelector,
  fetchAudiobooks,
  setSearchQuery,
  selectAudiobooksLoading,
  selectAudiobooksError,
  selectSearchQuery,
  selectFilteredAudiobooks,
  selectPremiumLibraryBooks,
  selectBasicLibraryBooks,
  selectConfiguringBooks,
  selectProcessingBooks,
} from '@/store'
import { cn } from '@/lib/utils'

type LibraryTab = 'all' | 'basic' | 'premium'

export default function Library() {
  const dispatch = useAppDispatch()
  const loading = useAppSelector(selectAudiobooksLoading)
  const error = useAppSelector(selectAudiobooksError)
  const searchQuery = useAppSelector(selectSearchQuery)

  const allBooks = useAppSelector(selectFilteredAudiobooks)
  const premiumBooks = useAppSelector(selectPremiumLibraryBooks)
  const basicBooks = useAppSelector(selectBasicLibraryBooks)
  const configuringBooks = useAppSelector(selectConfiguringBooks)
  const processingBooks = useAppSelector(selectProcessingBooks)

  const [activeTab, setActiveTab] = useState<LibraryTab>('all')
  
  // Fetch audiobooks on mount (uses cache if valid)
  useEffect(() => {
    dispatch(fetchAudiobooks())
  }, [dispatch])
  
  const handleSearchChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    dispatch(setSearchQuery(e.target.value))
  }

  // Books shown for current tab (search filtering is already applied by the selectors)
  const displayedBooks =
    activeTab === 'premium' ? premiumBooks
    : activeTab === 'basic' ? basicBooks
    : allBooks

  const tabCounts = {
    all: allBooks.length,
    basic: basicBooks.length,
    premium: premiumBooks.length,
  }

  const queueBooks = [...configuringBooks, ...processingBooks]

  return (
    <div className="container mx-auto px-4 py-8">
      {/* ================================================================== */}
      {/* PAGE HEADER */}
      {/* ================================================================== */}
      <div className="flex flex-col md:flex-row md:justify-between md:items-center gap-4 mb-6">
        <h1 className="text-3xl font-bold">My Library</h1>
        
        <div className="flex gap-3">
          {/* Search */}
          <div className="relative flex-1 md:w-64">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              type="search"
              placeholder="Search audiobooks..."
              value={searchQuery}
              onChange={handleSearchChange}
              className="pl-10"
            />
          </div>
          
          {/* Filter button */}
          <Button variant="outline" size="icon">
            <Filter className="h-4 w-4" />
          </Button>
          
          {/* Sort button */}
          <Button variant="outline" size="icon">
            <SortAsc className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {queueBooks.length > 0 && (
        <div className="mb-6 grid gap-4 lg:grid-cols-[0.8fr_1.2fr]">
          <Card className="border-border/70 bg-muted/20">
            <CardContent className="p-5">
              <p className="text-sm font-medium text-muted-foreground">Conversion queue</p>
              <div className="mt-3 grid grid-cols-2 gap-3">
                <div className="rounded-2xl border bg-background p-4">
                  <div className="text-2xl font-semibold">{configuringBooks.length}</div>
                  <div className="text-sm text-muted-foreground">Awaiting setup</div>
                </div>
                <div className="rounded-2xl border bg-background p-4">
                  <div className="text-2xl font-semibold">{processingBooks.length}</div>
                  <div className="text-sm text-muted-foreground">Actively converting</div>
                </div>
              </div>
              <p className="mt-3 text-sm text-muted-foreground">
                Uploaded PDFs now appear here before they become fully playable audiobooks.
              </p>
            </CardContent>
          </Card>

          <Card className="border-border/70">
            <CardContent className="p-5">
              <div className="mb-4">
                <p className="font-medium">Recent upload activity</p>
                <p className="text-sm text-muted-foreground">
                  These titles are using mock setup and progress data until the backend conversion workflow is finalized.
                </p>
              </div>
              <AudiobookList books={queueBooks.slice(0, 4)} />
            </CardContent>
          </Card>
        </div>
      )}

      {/* ================================================================== */}
      {/* TIER TABS */}
      {/* ================================================================== */}
      <div className="flex items-center gap-2 border-b mb-6">
        {/* All Tab */}
        <button
          onClick={() => setActiveTab('all')}
          className={cn(
            "flex items-center gap-2 px-4 py-2.5 text-sm font-medium border-b-2 -mb-px transition-colors",
            activeTab === 'all'
              ? "border-primary text-primary"
              : "border-transparent text-muted-foreground hover:text-foreground"
          )}
        >
          <BookOpen className="h-4 w-4" />
          All
          <span className={cn(
            "ml-1 text-xs px-1.5 py-0.5 rounded-full",
            activeTab === 'all' ? "bg-primary/10 text-primary" : "bg-muted text-muted-foreground"
          )}>
            {tabCounts.all}
          </span>
        </button>

        {/* Basic Tab */}
        <button
          onClick={() => setActiveTab('basic')}
          className={cn(
            "flex items-center gap-2 px-4 py-2.5 text-sm font-medium border-b-2 -mb-px transition-colors",
            activeTab === 'basic'
              ? "border-primary text-primary"
              : "border-transparent text-muted-foreground hover:text-foreground"
          )}
        >
          Basic
          <span className={cn(
            "ml-1 text-xs px-1.5 py-0.5 rounded-full",
            activeTab === 'basic' ? "bg-primary/10 text-primary" : "bg-muted text-muted-foreground"
          )}>
            {tabCounts.basic}
          </span>
        </button>

        {/* Premium Tab */}
        <button
          onClick={() => setActiveTab('premium')}
          className={cn(
            "flex items-center gap-2 px-4 py-2.5 text-sm font-medium border-b-2 -mb-px transition-colors",
            activeTab === 'premium'
              ? "border-amber-500 text-amber-600 dark:text-amber-400"
              : "border-transparent text-muted-foreground hover:text-amber-600 dark:hover:text-amber-400"
          )}
        >
          <Crown className={cn(
            "h-4 w-4",
            activeTab === 'premium' ? "text-amber-500" : ""
          )} />
          Premium
          <span className={cn(
            "ml-1 text-xs px-1.5 py-0.5 rounded-full",
            activeTab === 'premium' ? "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400" : "bg-muted text-muted-foreground"
          )}>
            {tabCounts.premium}
          </span>
        </button>
      </div>

      {/* ================================================================== */}
      {/* TAB DESCRIPTION */}
      {/* ================================================================== */}
      {activeTab === 'premium' && (
        <div className="flex items-start gap-3 p-4 mb-6 rounded-lg bg-amber-50 border border-amber-200 dark:bg-amber-900/10 dark:border-amber-800">
          <Gem className="h-5 w-5 text-amber-600 dark:text-amber-400 flex-shrink-0 mt-0.5" />
          <div>
            <p className="text-sm font-semibold text-amber-800 dark:text-amber-300">Theatrical Edition</p>
            <p className="text-sm text-amber-700 dark:text-amber-400">
              These audiobooks feature a full cast where each character is voiced by a dedicated AI voice, 
              creating an immersive, theatre-like experience.
            </p>
          </div>
        </div>
      )}

      {/* ================================================================== */}
      {/* ERROR STATE */}
      {/* ================================================================== */}
      {error && (
        <div className="text-center py-8 text-destructive">
          <p>{error}</p>
          <Button 
            variant="outline" 
            className="mt-4"
            onClick={() => dispatch(fetchAudiobooks())}
          >
            Try Again
          </Button>
        </div>
      )}
      
      {/* ================================================================== */}
      {/* LOADING STATE */}
      {/* ================================================================== */}
      {loading && !error && (
        <div className="text-center py-8 text-muted-foreground">
          <div className="animate-pulse">Loading audiobooks...</div>
        </div>
      )}
      
      {/* ================================================================== */}
      {/* AUDIOBOOK LIST */}
      {/* ================================================================== */}
      {!loading && !error && (
        <>
          {displayedBooks.length === 0 ? (
            <div className="text-center py-16 text-muted-foreground">
              {activeTab === 'premium' ? (
                <div className="space-y-3">
                  <Crown className="h-12 w-12 mx-auto text-amber-400/50" />
                  <p className="font-medium">No premium audiobooks yet</p>
                  <p className="text-sm">
                    Browse the store and look for the{' '}
                    <span className="font-semibold text-amber-600">Premium</span> badge to find theatrical editions.
                  </p>
                </div>
              ) : activeTab === 'basic' ? (
                <div className="space-y-3">
                  <BookOpen className="h-12 w-12 mx-auto text-muted-foreground/50" />
                  <p className="font-medium">No basic audiobooks yet</p>
                </div>
              ) : (
                <p>No audiobooks found</p>
              )}
            </div>
          ) : (
            <AudiobookList books={displayedBooks} />
          )}
        </>
      )}
    </div>
  )
}
