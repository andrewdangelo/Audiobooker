/**
 * AuthLayout Component
 * 
 * A centered layout wrapper for authentication pages with
 * a card-based design and optional branding.
 */

import { Link } from 'react-router-dom'
import { BookOpen } from 'lucide-react'

interface AuthLayoutProps {
  children: React.ReactNode
  title: string
  subtitle?: string
}

export default function AuthLayout({ children, title, subtitle }: AuthLayoutProps) {
  return (
    <div className="min-h-screen flex flex-col justify-center py-12 px-4 sm:px-6 lg:px-8 bg-muted/30">
      {/* Background decoration */}
      <div className="absolute inset-0 -z-10 overflow-hidden">
        <div className="absolute left-[50%] top-0 -z-10 -translate-x-1/2 blur-3xl" aria-hidden="true">
          <div 
            className="aspect-[1155/678] w-[72.1875rem] bg-gradient-to-tr from-primary/20 to-primary/5 opacity-30"
            style={{
              clipPath: 'polygon(74.1% 44.1%, 100% 61.6%, 97.5% 26.9%, 85.5% 0.1%, 80.7% 2%, 72.5% 32.5%, 60.2% 62.4%, 52.4% 68.1%, 47.5% 58.3%, 45.2% 34.5%, 27.5% 76.7%, 0.1% 64.9%, 17.9% 100%, 27.6% 76.8%, 76.1% 97.7%, 74.1% 44.1%)'
            }}
          />
        </div>
      </div>

      {/* Logo and Brand */}
      <div className="sm:mx-auto sm:w-full sm:max-w-md">
        <Link to="/" className="flex justify-center items-center gap-2 group">
          <div className="p-2 rounded-xl bg-primary text-primary-foreground group-hover:scale-105 transition-transform">
            <BookOpen className="h-8 w-8" />
          </div>
          <span className="text-2xl font-bold">Audion</span>
        </Link>
        
        <h2 className="mt-6 text-center text-3xl font-bold tracking-tight">
          {title}
        </h2>
        
        {subtitle && (
          <p className="mt-2 text-center text-sm text-muted-foreground">
            {subtitle}
          </p>
        )}
      </div>

      {/* Card Container */}
      <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-md">
        <div className="bg-card py-8 px-4 shadow-xl ring-1 ring-border/5 sm:rounded-xl sm:px-10">
          {children}
        </div>
      </div>

      {/* Footer */}
      <p className="mt-8 text-center text-xs text-muted-foreground">
        © {new Date().getFullYear()} Audion. All rights reserved.
      </p>
    </div>
  )
}
