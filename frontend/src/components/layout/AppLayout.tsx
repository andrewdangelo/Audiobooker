/**
 * AppLayout Component
 * 
 * Main layout wrapper for all authenticated pages.
 * Includes the sidebar navigation and top navbar.
 * Used as a route wrapper for all authenticated routes.
 * 
 * @author Andrew D'Angelo
 */

import { Outlet } from 'react-router-dom'
import { Sidebar } from './Sidebar'
import { Navbar } from './Navbar'
import { Toaster } from '@/components/ui/toaster'

interface AppLayoutProps {
  children?: React.ReactNode
}

export function AppLayout({ children }: AppLayoutProps) {
  // TODO: API Integration
  // - Check authentication status from /api/v1/auth/me
  // - If not authenticated, redirect to /login
  // - Fetch user data for navbar
  
  return (
    <div className="flex h-screen overflow-hidden bg-background">
      {/* Sidebar - Hidden on mobile, visible on md+ */}
      <div className="hidden md:flex">
        <Sidebar />
      </div>
      
      {/* Main Content Area */}
      <div className="flex flex-1 flex-col overflow-hidden">
        {/* Top Navbar */}
        <Navbar />
        
        {/* Page Content */}
        <main className="flex-1 overflow-y-auto">
          {children || <Outlet />}
        </main>
      </div>
      
      {/* Toast notifications */}
      <Toaster />
    </div>
  )
}

export default AppLayout
