# Frontend Development Guide

## Overview

The frontend is built with React 18, TypeScript, and Vite, providing a modern, fast development experience with type safety.

## Technology Stack

- **React 18**: UI library with hooks
- **TypeScript**: Type-safe JavaScript
- **Vite 5**: Next-generation frontend tooling
- **Tailwind CSS 3**: Utility-first CSS framework
- **shadcn/ui**: High-quality React components
- **React Router 6**: Client-side routing
- **Axios**: HTTP client for API calls

## Project Structure

```
frontend/
├── src/
│   ├── components/           # Reusable components
│   │   ├── ui/              # Base UI components (shadcn)
│   │   │   ├── button.tsx
│   │   │   ├── progress.tsx
│   │   │   └── ...
│   │   ├── layout/          # Layout components
│   │   │   ├── Header.tsx
│   │   │   ├── Footer.tsx
│   │   │   └── Sidebar.tsx
│   │   └── upload/          # Feature-specific components
│   │       ├── FileUpload.tsx
│   │       └── UploadProgress.tsx
│   ├── pages/               # Route-level components
│   │   ├── Home.tsx
│   │   ├── Dashboard.tsx
│   │   ├── Upload.tsx
│   │   ├── Library.tsx
│   │   └── NotFound.tsx
│   ├── services/            # API communication layer
│   │   ├── api.ts           # Axios configuration
│   │   ├── upload.service.ts
│   │   └── audiobook.service.ts
│   ├── hooks/               # Custom React hooks
│   │   └── useAudiobooks.ts
│   ├── types/               # TypeScript type definitions
│   │   ├── audiobook.ts
│   │   └── upload.ts
│   ├── utils/               # Utility functions
│   │   └── formatters.ts
│   ├── config/              # Configuration
│   │   └── env.ts
│   ├── App.tsx              # Root component
│   ├── main.tsx             # Entry point
│   └── index.css            # Global styles
├── public/                  # Static assets
├── index.html               # HTML template
├── package.json             # NPM dependencies
├── tsconfig.json            # TypeScript configuration
├── vite.config.ts           # Vite configuration
└── tailwind.config.js       # Tailwind CSS configuration
```

## Key Components

### FileUpload Component

The main component for handling PDF uploads with drag-and-drop functionality.

**Location**: `src/components/upload/FileUpload.tsx`

**Features**:
- Drag-and-drop support
- File type validation (PDF only)
- File size validation (max 50MB)
- Upload progress tracking
- Error handling
- Success feedback

**Usage**:
```tsx
import FileUpload from '@/components/upload/FileUpload'

function UploadPage() {
  return (
    <div>
      <h1>Upload PDF</h1>
      <FileUpload />
    </div>
  )
}
```

**State Management**:
```tsx
const [isDragging, setIsDragging] = useState(false)
const [selectedFile, setSelectedFile] = useState<File | null>(null)
const [uploading, setUploading] = useState(false)
const [progress, setProgress] = useState(0)
const [uploadResult, setUploadResult] = useState<any>(null)
const [error, setError] = useState<string | null>(null)
```

### UploadProgress Component

Displays upload progress with a progress bar.

**Location**: `src/components/upload/UploadProgress.tsx`

**Props**:
```tsx
interface UploadProgressProps {
  progress: number    // 0-100
  fileName: string    // Name of file being uploaded
}
```

## Services Layer

### API Configuration

**File**: `src/services/api.ts`

```typescript
import axios from 'axios'
import { API_BASE_URL } from '../config/env'

const api = axios.create({
  baseURL: API_BASE_URL,  // http://localhost:8000
  headers: {
    'Content-Type': 'application/json',
  },
})

// Request interceptor
api.interceptors.request.use(
  (config) => {
    // Add auth token here when implemented
    return config
  },
  (error) => Promise.reject(error)
)

// Response interceptor
api.interceptors.response.use(
  (response) => response,
  (error) => {
    // Handle common errors (401, 500, etc.)
    return Promise.reject(error)
  }
)

export default api
```

### Upload Service

**File**: `src/services/upload.service.ts`

```typescript
import api from './api'
import { UploadResponse } from '../types/upload'

export const uploadService = {
  async uploadPDF(file: File, onProgress?: (progress: number) => void): Promise<UploadResponse> {
    const formData = new FormData()
    formData.append('file', file)

    const response = await api.post('/api/v1/upload/', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      onUploadProgress: (progressEvent) => {
        if (progressEvent.total && onProgress) {
          const progress = Math.round((progressEvent.loaded * 100) / progressEvent.total)
          onProgress(progress)
        }
      },
    })

    return response.data
  },

  async getStatus(uploadId: string) {
    const response = await api.get(`/api/v1/upload/${uploadId}/status`)
    return response.data
  },
}
```

## TypeScript Types

### Upload Types

**File**: `src/types/upload.ts`

```typescript
export interface UploadResponse {
  id: string
  filename: string
  size: number
  message: string
  status: string
}

export interface UploadProgress {
  loaded: number
  total: number
  percentage: number
}

export interface UploadError {
  message: string
  code?: string
  details?: any
}
```

### Audiobook Types

**File**: `src/types/audiobook.ts`

```typescript
export interface Audiobook {
  id: string
  title: string
  original_file_name: string
  file_size: number
  pdf_path: string
  audio_path?: string
  status: AudiobookStatus
  created_at: string
  updated_at: string
}

export enum AudiobookStatus {
  PENDING = 'pending',
  PROCESSING = 'processing',
  COMPLETED = 'completed',
  FAILED = 'failed',
}
```

## Routing

**File**: `src/App.tsx`

```typescript
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import Home from './pages/Home'
import Dashboard from './pages/Dashboard'
import Upload from './pages/Upload'
import Library from './pages/Library'
import NotFound from './pages/NotFound'

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/upload" element={<Upload />} />
        <Route path="/library" element={<Library />} />
        <Route path="*" element={<NotFound />} />
      </Routes>
    </BrowserRouter>
  )
}
```

## Styling with Tailwind CSS

### Configuration

**File**: `tailwind.config.js`

```javascript
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          // Custom color palette
        },
      },
    },
  },
  plugins: [
    require("tailwindcss-animate"),
  ],
}
```

### Usage Example

```tsx
<div className="border-2 border-dashed rounded-lg p-8 text-center hover:border-gray-400">
  <p className="text-sm font-medium text-gray-900">
    Drop your PDF here
  </p>
</div>
```

## State Management

Currently using React Hooks for local state management:

- `useState`: Local component state
- `useEffect`: Side effects and lifecycle
- `useRef`: DOM references and mutable values
- Custom hooks: Reusable stateful logic

**Example Custom Hook** (`useAudiobooks.ts`):

```typescript
import { useState, useEffect } from 'react'
import { audiobookService } from '../services/audiobook.service'
import { Audiobook } from '../types/audiobook'

export function useAudiobooks() {
  const [audiobooks, setAudiobooks] = useState<Audiobook[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    loadAudiobooks()
  }, [])

  const loadAudiobooks = async () => {
    try {
      setLoading(true)
      const data = await audiobookService.getAll()
      setAudiobooks(data)
    } catch (err: any) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return { audiobooks, loading, error, reload: loadAudiobooks }
}
```

## Development Best Practices

### Component Structure

```tsx
// 1. Imports
import { useState } from 'react'
import { Button } from '@/components/ui/button'

// 2. Types/Interfaces
interface MyComponentProps {
  title: string
  onSubmit: () => void
}

// 3. Component
export default function MyComponent({ title, onSubmit }: MyComponentProps) {
  // 4. State
  const [value, setValue] = useState('')

  // 5. Effects
  useEffect(() => {
    // Effect logic
  }, [])

  // 6. Handlers
  const handleClick = () => {
    onSubmit()
  }

  // 7. Render
  return (
    <div>
      <h1>{title}</h1>
      <Button onClick={handleClick}>Submit</Button>
    </div>
  )
}
```

### Error Handling

```tsx
try {
  const result = await uploadService.uploadPDF(file, setProgress)
  setUploadResult(result)
} catch (err: any) {
  const errorMessage = err.response?.data?.detail 
    || err.message 
    || 'Upload failed'
  setError(errorMessage)
  console.error('Upload error:', err)
}
```

### Form Validation

```tsx
const handleFileSelect = (file: File) => {
  setError(null)
  
  // Validate file type
  if (!file.name.toLowerCase().endsWith('.pdf')) {
    setError('Please select a PDF file')
    return
  }
  
  // Validate file size (50MB max)
  if (file.size > 52428800) {
    setError('File size must be less than 50MB')
    return
  }
  
  setSelectedFile(file)
}
```

## Testing (Planned)

### Setup Vitest

```bash
npm install -D vitest @testing-library/react @testing-library/jest-dom
```

### Example Test

```typescript
import { render, screen } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import FileUpload from './FileUpload'

describe('FileUpload', () => {
  it('renders upload area', () => {
    render(<FileUpload />)
    expect(screen.getByText(/drop your pdf/i)).toBeInTheDocument()
  })
})
```

## Build and Deployment

### Development Build

```bash
npm run dev
```

### Production Build

```bash
npm run build

# Output directory: dist/
# - Optimized JavaScript bundles
# - Minified CSS
# - Hashed filenames for caching
```

### Preview Production Build

```bash
npm run preview
```

## Environment Configuration

**File**: `src/config/env.ts`

```typescript
export const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'
export const APP_NAME = import.meta.env.VITE_APP_NAME || 'Audiobooker'
export const MAX_FILE_SIZE = parseInt(import.meta.env.VITE_MAX_FILE_SIZE || '52428800')

export const isDevelopment = import.meta.env.DEV
export const isProduction = import.meta.env.PROD
```

## Performance Optimization

### Code Splitting

```tsx
import { lazy, Suspense } from 'react'

const Dashboard = lazy(() => import('./pages/Dashboard'))

function App() {
  return (
    <Suspense fallback={<div>Loading...</div>}>
      <Dashboard />
    </Suspense>
  )
}
```

### Memoization

```tsx
import { useMemo, useCallback } from 'react'

const memoizedValue = useMemo(() => computeExpensiveValue(a, b), [a, b])

const memoizedCallback = useCallback(() => {
  doSomething(a, b)
}, [a, b])
```

## Common Tasks

### Adding a New Page

1. Create component in `src/pages/NewPage.tsx`
2. Add route in `src/App.tsx`
3. Add navigation link in `src/components/layout/Header.tsx`

### Adding a New API Endpoint

1. Define types in `src/types/`
2. Add service method in `src/services/`
3. Use service in component

### Adding a New UI Component

1. Create component in `src/components/`
2. Export from `src/components/index.ts`
3. Import and use in pages/components
