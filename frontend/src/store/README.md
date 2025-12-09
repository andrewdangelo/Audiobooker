# Redux Store Documentation

## Overview

The Audion application uses **Redux Toolkit** for global state management with **redux-persist** for caching and persistence.

## Quick Start

### Using Redux in Components

```tsx
import { useAppDispatch, useAppSelector } from '@/store'
import { selectCurrentUser, logout } from '@/store'

function MyComponent() {
  const dispatch = useAppDispatch()
  const user = useAppSelector(selectCurrentUser)
  
  const handleLogout = () => {
    dispatch(logout())
  }
  
  return (
    <div>
      <p>Welcome, {user?.name}</p>
      <button onClick={handleLogout}>Logout</button>
    </div>
  )
}
```

## Store Structure

```
src/store/
├── index.ts          # Store configuration & exports
├── hooks.ts          # Typed useDispatch and useSelector hooks
├── Provider.tsx      # React provider component
├── README.md         # This documentation
└── slices/
    ├── index.ts          # Slice exports
    ├── authSlice.ts      # Authentication state
    ├── audioPlayerSlice.ts # Audio player state
    ├── audiobooksSlice.ts  # Audiobooks library & cache
    ├── uiSlice.ts        # UI state (modals, sidebar, theme)
    └── userSlice.ts      # User preferences & history
```

## Available Slices

### 1. Auth Slice (`authSlice.ts`)
Manages authentication state.

**State:**
- `isAuthenticated` - Whether user is logged in
- `user` - Current user object
- `token` - JWT token
- `loading` - Auth loading state
- `error` - Auth error message

**Actions:**
```tsx
import { login, logout, updateUser, loginAsync } from '@/store'

// Sync login (OAuth, etc.)
dispatch(login({ token: '...', user: {...} }))

// Async login
dispatch(loginAsync({ email, password }))

// Logout
dispatch(logout())
```

**Selectors:**
```tsx
import { selectIsAuthenticated, selectCurrentUser, selectAuthToken } from '@/store'

const isLoggedIn = useAppSelector(selectIsAuthenticated)
const user = useAppSelector(selectCurrentUser)
```

### 2. Audio Player Slice (`audioPlayerSlice.ts`)
Manages global audio playback state.

**State:**
- `currentTrack` - Currently playing audiobook
- `isPlaying` - Playback state
- `currentTime` / `duration` - Progress
- `playbackRate` / `volume` - Settings
- `queue` - Playback queue
- `repeatMode` / `shuffleEnabled` - Playback modes

**Actions:**
```tsx
import { 
  setCurrentTrack, play, pause, seek, 
  setPlaybackRate, setVolume, addToQueue 
} from '@/store'

dispatch(setCurrentTrack(audiobook))
dispatch(play())
dispatch(seek(120)) // Seek to 2 minutes
dispatch(setPlaybackRate(1.5))
```

**Selectors:**
```tsx
import { 
  selectCurrentTrack, selectIsPlaying, 
  selectProgress, selectCurrentChapter 
} from '@/store'

const track = useAppSelector(selectCurrentTrack)
const isPlaying = useAppSelector(selectIsPlaying)
const progress = useAppSelector(selectProgress) // 0-100%
```

### 3. Audiobooks Slice (`audiobooksSlice.ts`)
Manages audiobook library with caching.

**State:**
- `items` - Cached audiobooks by ID
- `ids` - Array of audiobook IDs
- `loading` - Loading state
- `error` - Error message
- `lastFetched` - Cache timestamp
- `searchQuery` / `activeFilters` / `sortBy` - Search/filter state

**Actions:**
```tsx
import { 
  fetchAudiobooks, fetchAudiobookById,
  updateProgress, toggleBookmark,
  setSearchQuery, setFilter, clearCache 
} from '@/store'

// Fetch all (uses cache if valid)
dispatch(fetchAudiobooks())

// Fetch specific audiobook
dispatch(fetchAudiobookById('audiobook-id'))

// Update progress
dispatch(updateProgress({ id: 'book-id', progress: 45 }))

// Search and filter
dispatch(setSearchQuery('gatsby'))
dispatch(setFilter({ key: 'genre', value: 'Fiction' }))
```

**Selectors:**
```tsx
import { 
  selectAllAudiobooks, selectAudiobookById,
  selectFilteredAudiobooks, selectBookmarkedAudiobooks,
  selectRecentlyPlayed, selectInProgressAudiobooks 
} from '@/store'

const allBooks = useAppSelector(selectAllAudiobooks)
const book = useAppSelector(state => selectAudiobookById(state, 'id'))
const filtered = useAppSelector(selectFilteredAudiobooks)
```

### 4. UI Slice (`uiSlice.ts`)
Manages UI state (not persisted).

**State:**
- `isSidebarOpen` / `isSidebarCollapsed`
- `activeModal` / `modalHistory`
- `theme` - 'light' | 'dark' | 'system'
- `toasts` - Toast notifications
- `isGlobalLoading`

**Actions:**
```tsx
import { 
  toggleSidebar, openModal, closeModal,
  setTheme, addToast, removeToast 
} from '@/store'

dispatch(toggleSidebar())
dispatch(openModal({ id: 'settings', props: {} }))
dispatch(setTheme('dark'))
dispatch(addToast({ type: 'success', title: 'Saved!' }))
```

### 5. User Slice (`userSlice.ts`)
Manages user preferences (persisted).

**State:**
- `preferences` - Playback/display/notification settings
- `listeningHistory` - Recent listening entries
- `recentSearches` - Search history
- `favoriteGenres`

**Actions:**
```tsx
import { 
  updatePreference, addToHistory,
  addRecentSearch, addFavoriteGenre 
} from '@/store'

dispatch(updatePreference({ key: 'defaultPlaybackSpeed', value: 1.25 }))
dispatch(addToHistory({ audiobookId: 'id', progress: 50, duration: 3600 }))
```

## Adding a New Slice

1. **Create the slice file** in `src/store/slices/`:

```tsx
// src/store/slices/myFeatureSlice.ts
import { createSlice, PayloadAction } from '@reduxjs/toolkit'
import type { RootState } from '../index'

interface MyFeatureState {
  data: string[]
  loading: boolean
}

const initialState: MyFeatureState = {
  data: [],
  loading: false,
}

const myFeatureSlice = createSlice({
  name: 'myFeature',
  initialState,
  reducers: {
    setData: (state, action: PayloadAction<string[]>) => {
      state.data = action.payload
    },
  },
})

export const { setData } = myFeatureSlice.actions
export const selectMyData = (state: RootState) => state.myFeature.data
export default myFeatureSlice.reducer
```

2. **Add to store** in `src/store/index.ts`:

```tsx
import myFeatureReducer from './slices/myFeatureSlice'

const rootReducer = combineReducers({
  // ... existing reducers
  myFeature: myFeatureReducer,
})

// If you want to persist it, add to whitelist:
const persistConfig = {
  // ...
  whitelist: ['auth', 'audioPlayer', 'user', 'myFeature'],
}
```

3. **Export from slices** in `src/store/slices/index.ts`:

```tsx
export * from './myFeatureSlice'
```

4. **Re-export from store** in `src/store/index.ts`:

```tsx
export * from './slices/myFeatureSlice'
```

## Persistence

The following slices are persisted to localStorage:
- `auth` - Keeps user logged in
- `audioPlayer` - Remembers last played track and position
- `user` - Keeps user preferences

To add/remove persistence, modify the `whitelist` in `persistConfig`.

## DevTools

Redux DevTools are enabled in development mode. Install the browser extension to inspect state and actions.

## Best Practices

1. **Always use typed hooks**: `useAppDispatch` and `useAppSelector`
2. **Create selectors** for computed/derived state
3. **Use async thunks** for API calls
4. **Keep state normalized** when possible
5. **Don't store UI state** that can be derived
6. **Use immer** (built into RTK) for immutable updates
