/**
 * Sidebar Component
 * 
 * Collapsible sidebar navigation for authenticated pages.
 * Contains links to Dashboard, Library, Store, Bookshelf, and more.
 * 
 * @author Andrew D'Angelo
 */

import { useState, createContext, useContext } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { 
  Library, 
  Store, 
  BookMarked, 
  ChevronLeft, 
  ChevronRight,
  Home,
  Upload,
  Settings,
  HelpCircle,
  List,
  Coins
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Tooltip } from '@/components/ui/tooltip'
import { Separator } from '@/components/ui/separator'

// Sidebar context for sharing collapsed state
interface SidebarContextType {
  isCollapsed: boolean
  setIsCollapsed: (value: boolean) => void
}

const SidebarContext = createContext<SidebarContextType>({
  isCollapsed: false,
  setIsCollapsed: () => {}
})

export const useSidebar = () => useContext(SidebarContext)

// Navigation items configuration
const mainNavItems = [
  { 
    icon: Home, 
    label: 'Dashboard', 
    href: '/dashboard',
    description: 'Dashboard overview'
  },
  { 
    icon: Library, 
    label: 'Library', 
    href: '/library',
    description: 'Browse your audiobooks'
  },
  { 
    icon: Store, 
    label: 'Store', 
    href: '/store',
    description: 'Discover new audiobooks'
    // TODO: API Integration - Fetch store catalog from /api/v1/store/catalog
  },
  { 
    icon: BookMarked, 
    label: 'Bookshelf', 
    href: '/bookshelf',
    description: 'Your saved books'
    // TODO: API Integration - Fetch user's bookshelf from /api/v1/users/{userId}/bookshelf
  },
]

const secondaryNavItems = [
  { 
    icon: Upload, 
    label: 'Upload', 
    href: '/upload',
    description: 'Upload new audiobooks'
  },
  { 
    icon: Coins, 
    label: 'Credits', 
    href: '/credits',
    description: 'Manage your credits and purchase history'
  },
  { 
    icon: List, 
    label: 'My Listings', 
    href: '/my-listings',
    description: 'Manage your store listings',
    permission: 'PUBLISH_AUDIOBOOK'
    // TODO: Only show to Publisher+ users
  },
  { 
    icon: Settings, 
    label: 'Settings', 
    href: '/settings',
    description: 'App settings'
    // TODO: API Integration - Fetch/update user settings from /api/v1/users/{userId}/settings
  },
  { 
    icon: HelpCircle, 
    label: 'Help', 
    href: '/help',
    description: 'Help & support'
  },
]

interface NavItemProps {
  icon: React.ElementType
  label: string
  href: string
  isCollapsed: boolean
  isActive: boolean
}

function NavItem({ icon: Icon, label, href, isCollapsed, isActive }: NavItemProps) {
  const baseClasses = `
    flex items-center gap-3 px-3 py-2.5 rounded-lg font-medium transition-all duration-200
    hover:bg-accent hover:text-accent-foreground
    focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring
  `
  
  const activeClasses = isActive 
    ? 'bg-primary/10 text-primary hover:bg-primary/15' 
    : 'text-muted-foreground'
  
  const content = (
    <Link 
      to={href} 
      className={`${baseClasses} ${activeClasses} ${isCollapsed ? 'justify-center' : ''}`}
    >
      <Icon className={`h-5 w-5 shrink-0 ${isActive ? 'text-primary' : ''}`} />
      {!isCollapsed && <span>{label}</span>}
    </Link>
  )
  
  if (isCollapsed) {
    return (
      <Tooltip content={label} side="right">
        {content}
      </Tooltip>
    )
  }
  
  return content
}

export function Sidebar() {
  const [isCollapsed, setIsCollapsed] = useState(false)
  const location = useLocation()
  
  return (
    <SidebarContext.Provider value={{ isCollapsed, setIsCollapsed }}>
      <aside 
        className={`
          relative flex flex-col border-r bg-card/50 backdrop-blur-sm
          transition-all duration-300 ease-in-out
          ${isCollapsed ? 'w-[70px]' : 'w-[240px]'}
        `}
      >
        {/* Logo Section */}
        <div className={`flex items-center h-16 px-4 border-b ${isCollapsed ? 'justify-center' : 'gap-3'}`}>
          <div className="flex items-center justify-center h-9 w-9 rounded-lg bg-primary text-primary-foreground">
            <BookMarked className="h-5 w-5" />
          </div>
          {!isCollapsed && (
            <span className="font-bold text-lg">Audion</span>
          )}
        </div>
        
        {/* Main Navigation */}
        <nav className="flex-1 p-3 space-y-1 overflow-y-auto">
          <div className="space-y-1">
            {!isCollapsed && (
              <span className="px-3 text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                Main
              </span>
            )}
            {mainNavItems.map((item) => (
              <NavItem
                key={item.href}
                icon={item.icon}
                label={item.label}
                href={item.href}
                isCollapsed={isCollapsed}
                isActive={location.pathname === item.href || 
                  (item.href !== '/dashboard' && location.pathname.startsWith(item.href))}
              />
            ))}
          </div>
          
          <Separator className="my-4" />
          
          <div className="space-y-1">
            {!isCollapsed && (
              <span className="px-3 text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                Other
              </span>
            )}
            {secondaryNavItems.map((item) => (
              <NavItem
                key={item.href}
                icon={item.icon}
                label={item.label}
                href={item.href}
                isCollapsed={isCollapsed}
                isActive={location.pathname === item.href}
              />
            ))}
          </div>
        </nav>
        
        {/* Collapse Toggle Button */}
        <div className="p-3 border-t">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setIsCollapsed(!isCollapsed)}
            className={`w-full ${isCollapsed ? 'justify-center px-0' : 'justify-start'}`}
            aria-label={isCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          >
            {isCollapsed ? (
              <ChevronRight className="h-4 w-4" />
            ) : (
              <>
                <ChevronLeft className="h-4 w-4 mr-2" />
                <span>Collapse</span>
              </>
            )}
          </Button>
        </div>
      </aside>
    </SidebarContext.Provider>
  )
}

export default Sidebar
