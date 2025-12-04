/**
 * Dashboard Page
 * 
 * Main dashboard showing overview statistics, recent activity,
 * and quick actions for the user.
 * 
 * @author Andrew D'Angelo
 */

import { Link } from 'react-router-dom'
import { 
  BookOpen, 
  Clock, 
  Headphones, 
  TrendingUp, 
  Play, 
  Upload,
  ArrowRight,
  Sparkles
} from 'lucide-react'
import { Button } from '@/components/ui/button'

// TODO: API Integration Points
// - GET /api/v1/users/{userId}/stats - Fetch user statistics
// - GET /api/v1/users/{userId}/activity - Fetch recent activity
// - GET /api/v1/users/{userId}/continue-listening - Fetch continue listening items
// - GET /api/v1/recommendations - Fetch personalized recommendations

// Mock data - replace with API calls
const mockStats = {
  totalBooks: 12,
  hoursListened: 48.5,
  booksInProgress: 3,
  completedThisMonth: 2
}

const mockContinueListening = [
  {
    id: 'demo-great-gatsby',
    title: 'The Great Gatsby',
    author: 'F. Scott Fitzgerald',
    progress: 65,
    lastPlayed: '2 hours ago',
    coverImage: undefined
  },
  {
    id: 'demo-1984',
    title: '1984',
    author: 'George Orwell',
    progress: 23,
    lastPlayed: 'Yesterday',
    coverImage: undefined
  }
]

const mockRecentActivity = [
  { type: 'listened', title: 'The Great Gatsby', time: '2 hours ago' },
  { type: 'bookmarked', title: '1984', time: 'Yesterday' },
  { type: 'completed', title: 'Pride and Prejudice', time: '3 days ago' },
  { type: 'uploaded', title: 'New Audiobook', time: '1 week ago' }
]

export default function Dashboard() {
  return (
    <div className="p-6 md:p-8 space-y-8 max-w-7xl mx-auto">
      {/* Welcome Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Welcome back!</h1>
          <p className="text-muted-foreground mt-1">
            Here's what's happening with your audiobooks
          </p>
        </div>
        <div className="flex gap-3">
          <Button asChild variant="outline">
            <Link to="/library">
              <BookOpen className="h-4 w-4 mr-2" />
              Browse Library
            </Link>
          </Button>
          <Button asChild>
            <Link to="/upload">
              <Upload className="h-4 w-4 mr-2" />
              Upload New
            </Link>
          </Button>
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          icon={BookOpen}
          label="Total Audiobooks"
          value={mockStats.totalBooks.toString()}
          trend="+2 this month"
          trendUp={true}
        />
        <StatCard
          icon={Clock}
          label="Hours Listened"
          value={`${mockStats.hoursListened}h`}
          trend="+12h this week"
          trendUp={true}
        />
        <StatCard
          icon={Headphones}
          label="In Progress"
          value={mockStats.booksInProgress.toString()}
          subtitle="books"
        />
        <StatCard
          icon={TrendingUp}
          label="Completed"
          value={mockStats.completedThisMonth.toString()}
          subtitle="this month"
        />
      </div>

      {/* Main Content Grid */}
      <div className="grid lg:grid-cols-3 gap-6">
        {/* Continue Listening - Takes 2 columns */}
        <div className="lg:col-span-2 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-xl font-semibold">Continue Listening</h2>
            <Button variant="ghost" size="sm" asChild>
              <Link to="/library" className="text-muted-foreground">
                View all <ArrowRight className="h-4 w-4 ml-1" />
              </Link>
            </Button>
          </div>
          
          {mockContinueListening.length > 0 ? (
            <div className="grid sm:grid-cols-2 gap-4">
              {mockContinueListening.map((book) => (
                <ContinueListeningCard key={book.id} {...book} />
              ))}
            </div>
          ) : (
            <EmptyState
              icon={Headphones}
              title="No audiobooks in progress"
              description="Start listening to an audiobook from your library"
              actionLabel="Browse Library"
              actionHref="/library"
            />
          )}
        </div>

        {/* Recent Activity - Takes 1 column */}
        <div className="space-y-4">
          <h2 className="text-xl font-semibold">Recent Activity</h2>
          <div className="rounded-xl border bg-card p-4 space-y-4">
            {mockRecentActivity.length > 0 ? (
              mockRecentActivity.map((activity, index) => (
                <ActivityItem key={index} {...activity} />
              ))
            ) : (
              <p className="text-muted-foreground text-sm text-center py-4">
                No recent activity
              </p>
            )}
          </div>
        </div>
      </div>

      {/* Quick Actions */}
      <div className="space-y-4">
        <h2 className="text-xl font-semibold">Quick Actions</h2>
        <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <QuickActionCard
            icon={Upload}
            title="Upload Audiobook"
            description="Add a new audiobook to your library"
            href="/upload"
          />
          <QuickActionCard
            icon={BookOpen}
            title="Browse Library"
            description="Explore your audiobook collection"
            href="/library"
          />
          <QuickActionCard
            icon={Sparkles}
            title="Discover"
            description="Find new audiobooks to enjoy"
            href="/store"
          />
          <QuickActionCard
            icon={Headphones}
            title="Player Demo"
            description="Test the audio player features"
            href="/player-demo"
          />
        </div>
      </div>
    </div>
  )
}

// ==================== Sub-components ====================

interface StatCardProps {
  icon: React.ElementType
  label: string
  value: string
  trend?: string
  trendUp?: boolean
  subtitle?: string
}

function StatCard({ icon: Icon, label, value, trend, trendUp, subtitle }: StatCardProps) {
  return (
    <div className="rounded-xl border bg-card p-5 space-y-3">
      <div className="flex items-center gap-2 text-muted-foreground">
        <Icon className="h-4 w-4" />
        <span className="text-sm font-medium">{label}</span>
      </div>
      <div>
        <span className="text-3xl font-bold">{value}</span>
        {subtitle && (
          <span className="text-muted-foreground text-sm ml-1">{subtitle}</span>
        )}
      </div>
      {trend && (
        <p className={`text-xs ${trendUp ? 'text-green-600' : 'text-muted-foreground'}`}>
          {trend}
        </p>
      )}
    </div>
  )
}

interface ContinueListeningCardProps {
  id: string
  title: string
  author: string
  progress: number
  lastPlayed: string
  coverImage?: string
}

function ContinueListeningCard({ id, title, author, progress, lastPlayed, coverImage }: ContinueListeningCardProps) {
  return (
    <Link 
      to={`/book/${id}`}
      className="flex gap-4 p-4 rounded-xl border bg-card hover:bg-accent/50 transition-colors group"
    >
      {/* Cover */}
      <div className="relative w-16 h-20 rounded-lg overflow-hidden bg-muted shrink-0">
        {coverImage ? (
          <img src={coverImage} alt={title} className="w-full h-full object-cover" />
        ) : (
          <div className="w-full h-full flex items-center justify-center bg-gradient-to-br from-primary/20 to-primary/40">
            <BookOpen className="h-6 w-6 text-primary/60" />
          </div>
        )}
        {/* Play overlay */}
        <div className="absolute inset-0 flex items-center justify-center bg-black/40 opacity-0 group-hover:opacity-100 transition-opacity">
          <Play className="h-6 w-6 text-white" fill="currentColor" />
        </div>
      </div>
      
      {/* Info */}
      <div className="flex-1 min-w-0 space-y-2">
        <div>
          <h3 className="font-medium truncate group-hover:text-primary transition-colors">
            {title}
          </h3>
          <p className="text-sm text-muted-foreground truncate">{author}</p>
        </div>
        
        {/* Progress bar */}
        <div className="space-y-1">
          <div className="h-1.5 bg-muted rounded-full overflow-hidden">
            <div 
              className="h-full bg-primary rounded-full transition-all"
              style={{ width: `${progress}%` }}
            />
          </div>
          <div className="flex justify-between text-xs text-muted-foreground">
            <span>{progress}% complete</span>
            <span>{lastPlayed}</span>
          </div>
        </div>
      </div>
    </Link>
  )
}

interface ActivityItemProps {
  type: string
  title: string
  time: string
}

function ActivityItem({ type, title, time }: ActivityItemProps) {
  const getActivityIcon = () => {
    switch (type) {
      case 'listened': return <Headphones className="h-4 w-4" />
      case 'bookmarked': return <BookOpen className="h-4 w-4" />
      case 'completed': return <TrendingUp className="h-4 w-4" />
      case 'uploaded': return <Upload className="h-4 w-4" />
      default: return <Clock className="h-4 w-4" />
    }
  }
  
  const getActivityText = () => {
    switch (type) {
      case 'listened': return 'Listened to'
      case 'bookmarked': return 'Bookmarked'
      case 'completed': return 'Completed'
      case 'uploaded': return 'Uploaded'
      default: return 'Activity on'
    }
  }
  
  return (
    <div className="flex items-start gap-3">
      <div className="p-2 rounded-full bg-muted text-muted-foreground">
        {getActivityIcon()}
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-sm">
          <span className="text-muted-foreground">{getActivityText()}</span>{' '}
          <span className="font-medium">{title}</span>
        </p>
        <p className="text-xs text-muted-foreground">{time}</p>
      </div>
    </div>
  )
}

interface QuickActionCardProps {
  icon: React.ElementType
  title: string
  description: string
  href: string
}

function QuickActionCard({ icon: Icon, title, description, href }: QuickActionCardProps) {
  return (
    <Link 
      to={href}
      className="flex flex-col p-5 rounded-xl border bg-card hover:bg-accent/50 hover:border-accent transition-all group"
    >
      <div className="p-2 rounded-lg bg-primary/10 text-primary w-fit mb-3 group-hover:bg-primary group-hover:text-primary-foreground transition-colors">
        <Icon className="h-5 w-5" />
      </div>
      <h3 className="font-medium mb-1">{title}</h3>
      <p className="text-sm text-muted-foreground">{description}</p>
    </Link>
  )
}

interface EmptyStateProps {
  icon: React.ElementType
  title: string
  description: string
  actionLabel: string
  actionHref: string
}

function EmptyState({ icon: Icon, title, description, actionLabel, actionHref }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center p-8 rounded-xl border bg-card text-center">
      <div className="p-3 rounded-full bg-muted mb-4">
        <Icon className="h-6 w-6 text-muted-foreground" />
      </div>
      <h3 className="font-medium mb-1">{title}</h3>
      <p className="text-sm text-muted-foreground mb-4">{description}</p>
      <Button asChild size="sm">
        <Link to={actionHref}>{actionLabel}</Link>
      </Button>
    </div>
  )
}
