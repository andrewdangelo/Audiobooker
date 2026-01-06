/**
 * Library Page
 * 
 * Displays the user's audiobook library with search and filter capabilities.
 * Uses Redux for state management and caching.
 * 
 * @author Andrew D'Angelo
 */

import { useEffect } from 'react'
import { Search, Filter, SortAsc } from 'lucide-react'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import AudiobookList from '../components/audiobook/AudiobookList'
import { 
  useAppDispatch, 
  useAppSelector,
  fetchAudiobooks,
  setSearchQuery,
  selectAudiobooksLoading,
  selectAudiobooksError,
  selectSearchQuery,
} from '@/store'

export default function Library() {
  const dispatch = useAppDispatch()
  const loading = useAppSelector(selectAudiobooksLoading)
  const error = useAppSelector(selectAudiobooksError)
  const searchQuery = useAppSelector(selectSearchQuery)
  
  // Fetch audiobooks on mount (uses cache if valid)
  useEffect(() => {
    dispatch(fetchAudiobooks())
  }, [dispatch])
  
  const handleSearchChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    dispatch(setSearchQuery(e.target.value))
  }
  
  return (
    <div className="container mx-auto px-4 py-8">
      <div className="flex flex-col md:flex-row md:justify-between md:items-center gap-4 mb-8">
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
      
      {/* Error state */}
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
      
      {/* Loading state */}
      {loading && !error && (
        <div className="text-center py-8 text-muted-foreground">
          <div className="animate-pulse">Loading audiobooks...</div>
        </div>
      )}
      
      {/* Audiobook list */}
      {!loading && !error && <AudiobookList />}
    </div>
  )
}
