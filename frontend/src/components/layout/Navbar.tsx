/**
 * Navbar Component
 * 
 * Top navigation bar for authenticated pages with search, cart, and user profile.
 * 
 * @author Andrew D'Angelo
 */

import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { 
  Search, 
  Bell, 
  User,
  Settings,
  LogOut,
  HelpCircle,
  Moon,
  Sun,
  BookMarked,
  ShoppingCart,
  Coins
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Avatar } from '@/components/ui/avatar'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { Separator } from '@/components/ui/separator'
import { useAppSelector, useAppDispatch } from '@/store/hooks'
import { selectCartItemCount } from '@/store/slices/cartSlice'
import { selectCurrentUser, selectUserDisplayName, logout } from '@/store/slices/authSlice'
import { selectUserCredits } from '@/store/slices/storeSlice'
import { authService } from '@/services/authService'

export function Navbar() {
  const [searchQuery, setSearchQuery] = useState('')
  const [isDarkMode, setIsDarkMode] = useState(false)
  const navigate = useNavigate()
  const dispatch = useAppDispatch()
  
  // Cart item count from Redux
  const cartItemCount = useAppSelector(selectCartItemCount)
  
  // User data from Redux auth state
  const user = useAppSelector(selectCurrentUser)
  const displayName = useAppSelector(selectUserDisplayName)
  
  // Credits from Redux store state
  const userCredits = useAppSelector(selectUserCredits)
  
  // Computed user display values
  const currentUser = {
    name: displayName,
    email: user?.email || '',
    avatarUrl: user?.avatarUrl,
    credits: userCredits
  }
  
  // TODO: Implement actual search functionality
  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault()
    console.log('Search query:', searchQuery)
    // TODO: API call to /api/v1/search?q={searchQuery}
  }
  
  // Handle logout
  const handleLogout = async () => {
    try {
      // Clear tokens from localStorage
      authService.clearTokens()
      // Dispatch logout action to Redux
      dispatch(logout())
      // Navigate to login page
      navigate('/login')
    } catch (error) {
      console.error('Logout error:', error)
    }
  }
  
  // TODO: Implement actual theme toggle with context
  const toggleTheme = () => {
    setIsDarkMode(!isDarkMode)
    document.documentElement.classList.toggle('dark')
  }
  
  return (
    <header className="sticky top-0 z-40 h-16 border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="flex h-full items-center justify-between px-4 md:px-6">
        {/* Left Section - Logo (visible on mobile) & Search */}
        <div className="flex items-center gap-4 flex-1">
          {/* Mobile Logo - Hidden on larger screens where sidebar is visible */}
          <Link to="/dashboard" className="flex items-center gap-2 md:hidden">
            <div className="flex items-center justify-center h-8 w-8 rounded-lg bg-primary text-primary-foreground">
              <BookMarked className="h-4 w-4" />
            </div>
          </Link>
          
          {/* Search Bar */}
          <form onSubmit={handleSearch} className="hidden sm:flex flex-1 max-w-md">
            <div className="relative w-full">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                type="search"
                placeholder="Search audiobooks..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-10 h-10 w-full rounded-lg border bg-muted/50 focus:bg-background"
              />
            </div>
          </form>
        </div>
        
        {/* Right Section - Actions & Profile */}
        <div className="flex items-center gap-2">
          {/* Mobile Search Button */}
          <Button variant="ghost" size="icon" className="sm:hidden">
            <Search className="h-5 w-5" />
            <span className="sr-only">Search</span>
          </Button>
          
          {/* Credits Button */}
          <Button 
            variant="outline" 
            size="sm"
            className="hidden sm:flex items-center gap-2 font-semibold"
            asChild
          >
            <Link to="/credits">
              <Coins className="h-4 w-4" />
              <span>{currentUser.credits} Credits</span>
            </Link>
          </Button>
          
          {/* Theme Toggle */}
          <Button 
            variant="ghost" 
            size="icon"
            onClick={toggleTheme}
            aria-label="Toggle theme"
          >
            {isDarkMode ? (
              <Sun className="h-5 w-5" />
            ) : (
              <Moon className="h-5 w-5" />
            )}
          </Button>
          
          {/* Shopping Cart */}
          <Button 
            variant="ghost" 
            size="icon" 
            className="relative"
            asChild
          >
            <Link to="/cart" aria-label="Shopping cart">
              <ShoppingCart className="h-5 w-5" />
              {cartItemCount > 0 && (
                <span className="absolute -top-1 -right-1 h-5 w-5 rounded-full bg-primary text-primary-foreground text-xs font-medium flex items-center justify-center">
                  {cartItemCount > 9 ? '9+' : cartItemCount}
                </span>
              )}
              <span className="sr-only">Cart ({cartItemCount} items)</span>
            </Link>
          </Button>
          
          {/* Notifications */}
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" size="icon" className="relative">
                <Bell className="h-5 w-5" />
                {/* Notification Badge - TODO: Show actual count from API */}
                <span className="absolute top-1.5 right-1.5 h-2 w-2 rounded-full bg-destructive" />
                <span className="sr-only">Notifications</span>
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-80">
              <div className="flex items-center justify-between px-4 py-3 border-b">
                <span className="font-semibold">Notifications</span>
                <Button variant="ghost" size="sm" className="text-xs text-muted-foreground">
                  Mark all read
                </Button>
              </div>
              <div className="py-4 px-4 text-center text-sm text-muted-foreground">
                {/* TODO: Map through notifications from API */}
                No new notifications
              </div>
              <Separator />
              <div className="p-2">
                <Link to="/notifications">
                  <Button variant="ghost" size="sm" className="w-full justify-center">
                    View all notifications
                  </Button>
                </Link>
              </div>
            </DropdownMenuContent>
          </DropdownMenu>
          
          {/* User Profile Dropdown */}
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button 
                variant="ghost" 
                className="relative h-10 w-10 rounded-full p-0 hover:ring-2 hover:ring-ring hover:ring-offset-2"
              >
                <Avatar
                  src={currentUser.avatarUrl}
                  alt={currentUser.name}
                  fallback={currentUser.name.charAt(0)}
                  size="md"
                />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-56">
              {/* User Info */}
              <div className="flex items-center gap-3 px-3 py-3 border-b">
                <Avatar
                  src={currentUser.avatarUrl}
                  alt={currentUser.name}
                  fallback={currentUser.name.charAt(0)}
                  size="md"
                />
                <div className="flex flex-col space-y-0.5">
                  <span className="text-sm font-medium">{currentUser.name}</span>
                  <span className="text-xs text-muted-foreground">{currentUser.email}</span>
                </div>
              </div>
              
              {/* Menu Items */}
              <div className="p-1">
                <DropdownMenuItem asChild className="cursor-pointer">
                  <Link to="/profile" className="flex items-center gap-2">
                    <User className="h-4 w-4" />
                    <span>Profile</span>
                  </Link>
                </DropdownMenuItem>
                <DropdownMenuItem asChild className="cursor-pointer">
                  <Link to="/settings" className="flex items-center gap-2">
                    <Settings className="h-4 w-4" />
                    <span>Settings</span>
                  </Link>
                </DropdownMenuItem>
                <DropdownMenuItem asChild className="cursor-pointer">
                  <Link to="/help" className="flex items-center gap-2">
                    <HelpCircle className="h-4 w-4" />
                    <span>Help & Support</span>
                  </Link>
                </DropdownMenuItem>
              </div>
              
              <Separator />
              
              {/* Logout */}
              <div className="p-1">
                <DropdownMenuItem 
                  onClick={handleLogout}
                  className="cursor-pointer text-destructive focus:text-destructive"
                >
                  <LogOut className="h-4 w-4 mr-2" />
                  <span>Log out</span>
                </DropdownMenuItem>
              </div>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </div>
    </header>
  )
}

export default Navbar
