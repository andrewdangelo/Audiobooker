/**
 * Protected Route Component
 * 
 * Wraps routes that require authentication.
 * Redirects to login page if user is not authenticated.
 * 
 * @author Andrew D'Angelo
 */

import { Navigate, useLocation } from 'react-router-dom'
import { useAppSelector } from '@/store/hooks'
import { selectIsAuthenticated, selectAuthLoading } from '@/store/slices/authSlice'
import { authService } from '@/services/authService'

interface ProtectedRouteProps {
  children: React.ReactNode
}

export function ProtectedRoute({ children }: ProtectedRouteProps) {
  const location = useLocation()
  const isAuthenticated = useAppSelector(selectIsAuthenticated)
  const isLoading = useAppSelector(selectAuthLoading)
  
  // Also check localStorage for token (in case Redux hasn't hydrated yet)
  const hasToken = authService.isAuthenticated()
  
  // Show nothing while loading auth state
  if (isLoading) {
    return (
      <div className="flex h-screen items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
      </div>
    )
  }
  
  // Redirect to login if not authenticated
  if (!isAuthenticated && !hasToken) {
    // Save the attempted location for redirect after login
    return <Navigate to="/login" state={{ from: location }} replace />
  }
  
  return <>{children}</>
}

export default ProtectedRoute
