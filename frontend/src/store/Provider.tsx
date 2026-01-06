/**
 * Redux Store Provider
 * 
 * Wraps the application with Redux store and persistence.
 * Import this component and wrap your app in main.tsx.
 * 
 * @example
 * // In main.tsx:
 * import { StoreProvider } from '@/store/Provider'
 * 
 * ReactDOM.createRoot(document.getElementById('root')!).render(
 *   <StoreProvider>
 *     <App />
 *   </StoreProvider>
 * )
 */

import { Provider } from 'react-redux'
import { PersistGate } from 'redux-persist/integration/react'
import { store, persistor } from './index'

interface StoreProviderProps {
  children: React.ReactNode
}

export function StoreProvider({ children }: StoreProviderProps) {
  return (
    <Provider store={store}>
      <PersistGate 
        loading={
          <div className="flex items-center justify-center min-h-screen">
            <div className="animate-pulse text-muted-foreground">Loading...</div>
          </div>
        } 
        persistor={persistor}
      >
        {children}
      </PersistGate>
    </Provider>
  )
}

export default StoreProvider
