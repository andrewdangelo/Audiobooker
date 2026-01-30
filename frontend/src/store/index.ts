/**
 * Redux Store Configuration
 * 
 * Central store configuration for the Audion application.
 * Uses Redux Toolkit for simplified state management with built-in
 * immutability, DevTools support, and TypeScript integration.
 * 
 * @author Andrew D'Angelo
 * @version 1.0.0
 * 
 * HOW TO ADD A NEW SLICE:
 * 1. Create a new file in src/store/slices/ (e.g., myFeatureSlice.ts)
 * 2. Import and add the reducer to the rootReducer below
 * 3. Export any selectors and actions from this index file
 */

import { configureStore, combineReducers } from '@reduxjs/toolkit'
import { 
  persistStore, 
  persistReducer,
  FLUSH,
  REHYDRATE,
  PAUSE,
  PERSIST,
  PURGE,
  REGISTER,
} from 'redux-persist'
import storage from 'redux-persist/lib/storage'

// Import slices
import authReducer from './slices/authSlice'
import audioPlayerReducer from './slices/audioPlayerSlice'
import audiobooksReducer from './slices/audiobooksSlice'
import uiReducer from './slices/uiSlice'
import userReducer from './slices/userSlice'
import storeReducer from './slices/storeSlice'
import cartReducer from './slices/cartSlice'
import subscriptionReducer from './slices/subscriptionSlice'

// Combine all reducers
const rootReducer = combineReducers({
  auth: authReducer,
  audioPlayer: audioPlayerReducer,
  audiobooks: audiobooksReducer,
  ui: uiReducer,
  user: userReducer,
  store: storeReducer,
  cart: cartReducer,
  subscription: subscriptionReducer,
})

// Persist configuration - choose which slices to persist
const persistConfig = {
  key: 'audion-root',
  version: 1,
  storage,
  // Whitelist: only these slices will be persisted
  whitelist: ['auth', 'audioPlayer', 'user', 'cart', 'subscription'],
  // Blacklist: these slices will NOT be persisted (takes precedence over whitelist)
  // blacklist: ['ui'],
}

// Create persisted reducer
const persistedReducer = persistReducer(persistConfig, rootReducer)

// Configure store with middleware
export const store = configureStore({
  reducer: persistedReducer,
  middleware: (getDefaultMiddleware) =>
    getDefaultMiddleware({
      serializableCheck: {
        // Ignore redux-persist actions for serializable check
        ignoredActions: [FLUSH, REHYDRATE, PAUSE, PERSIST, PURGE, REGISTER],
      },
    }),
  devTools: import.meta.env.DEV,
})

// Create persistor for redux-persist
export const persistor = persistStore(store)

// Infer types from the store itself
export type RootState = ReturnType<typeof rootReducer>
export type AppDispatch = typeof store.dispatch

// Re-export hooks and selectors for convenience
export * from './hooks'
export * from './slices/authSlice'
export * from './slices/audioPlayerSlice'
export * from './slices/audiobooksSlice'
export * from './slices/uiSlice'
export * from './slices/userSlice'
export * from './slices/storeSlice'
export * from './slices/cartSlice'
export * from './slices/subscriptionSlice'
