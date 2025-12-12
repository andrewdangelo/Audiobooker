# Audiobook Preview Feature - UI Design Documentation

## Overview
This document describes the audiobook preview page UI that appears after a user uploads their book file for TTS conversion. The interface supports three credit tiers with different preview experiences.

## File Structure

### New Files Created

```
frontend/src/
├── types/
│   └── preview.ts                           # TypeScript types for preview features
├── components/audiobook/
│   ├── ProcessingStatus.tsx                 # Upload/processing feedback component
│   ├── VoicePreview.tsx                     # Audio preview player component
│   └── VoiceSelector.tsx                    # Voice selection dropdown for authors
└── pages/
    └── AudiobookPreview.tsx                 # Main preview page
```

## Components

### 1. ProcessingStatus Component
**Location:** `src/components/audiobook/ProcessingStatus.tsx`

**Purpose:** Displays upload and TTS processing status with progress indicators

**Features:**
- Visual status indicators (spinner, checkmark, error icon)
- Progress bar with percentage
- Estimated completion time
- Error message display
- Auto-updates via polling

**Backend Integration Points:**
```typescript
// Poll for status updates
GET /api/previews/{previewId}/status

Response:
{
  status: 'uploading' | 'processing' | 'completed' | 'failed',
  progress: 0-100,
  estimatedTime: string,
  errorMessage?: string
}
```

### 2. VoicePreview Component
**Location:** `src/components/audiobook/VoicePreview.tsx`

**Purpose:** Custom audio player for previewing voice samples

**Features:**
- Play/pause controls
- Progress bar with time display
- Character name and voice information
- Theatrical badge for premium voices
- Responsive design

**Backend Integration Points:**
```typescript
// Fetch audio samples
Basic: GET /api/previews/{previewId}/basic-voice-sample
Premium: GET /api/previews/{previewId}/character-samples

// Response: Audio file stream or URL
// Ensure CORS is configured for audio file access
```

### 3. VoiceSelector Component
**Location:** `src/components/audiobook/VoiceSelector.tsx`

**Purpose:** Dropdown menu for selecting voices per character (Author/Publisher tier)

**Features:**
- Character information display
- Dropdown with voice options (name, gender, accent)
- Live voice preview
- Visual feedback for selection

**Backend Integration Points:**
```typescript
// Fetch available voices
GET /api/voices/available?gender=all&accent=all

Response:
{
  voices: [
    {
      id: string,
      name: string,
      description: string,
      gender: 'male' | 'female' | 'neutral',
      accent: string,
      sampleUrl: string
    }
  ]
}

// Update character voice selection
PUT /api/previews/{previewId}/character-voices

Body:
{
  characterName: string,
  voiceId: string
}
```

### 4. AudiobookPreview Page
**Location:** `src/pages/AudiobookPreview.tsx`

**Purpose:** Main page orchestrating the entire preview experience

**Features:**
- Dynamic content based on credit type
- Status polling for processing updates
- Three distinct UI modes (Basic, Premium, Author/Publisher)
- Confirmation and conversion flow

**Backend Integration Points:**
```typescript
// Initial data fetch
GET /api/previews/{previewId}

Response:
{
  id: string,
  audiobookId: string,
  creditType: 'basic' | 'premium' | 'author_publisher',
  processingStatus: 'uploading' | 'processing' | 'completed' | 'failed',
  processingProgress: 0-100,
  basicVoicePreviewUrl?: string,
  characterVoices?: CharacterVoice[],
  availableVoices?: VoiceOption[],
  estimatedCompletionTime?: string,
  errorMessage?: string
}

// Confirm and start full conversion
POST /api/previews/{previewId}/confirm

// This should queue the full TTS conversion job
```

## Credit Type UI Variations

### Basic Credit
**UI Elements:**
- Single voice preview player
- Label: "Basic Credit Plan"
- Description: "Single professional voice narration for your entire audiobook"
- Simple play/pause controls
- One-click confirmation

**User Flow:**
1. Upload completes → Processing status shown
2. Processing completes → Single voice preview displayed
3. User listens to sample
4. User confirms → Full conversion starts

### Premium Credit
**UI Elements:**
- Multiple voice preview players (one per character)
- Label: "Premium Credit Plan"
- Badge: "Theatrical" on each character preview
- Description: "Theatrical experience with multiple character voices"
- Grid layout for character voices

**User Flow:**
1. Upload completes → Processing status shown
2. Processing completes → Multiple character previews displayed
3. User listens to different character voices
4. User confirms → Full conversion starts with assigned voices

### Author/Publisher Credit
**UI Elements:**
- Voice selector cards for each character
- Label: "Author/Publisher Plan"
- Dropdown menus for voice selection
- Live preview updates when voice changes
- Character descriptions
- Description: "Custom voice selection for each character"

**User Flow:**
1. Upload completes → Processing status shown
2. Processing completes → Character voice selectors displayed
3. User selects voice for each character from dropdown
4. User previews each selection
5. User confirms → Full conversion starts with custom voice assignments

## TypeScript Types

### Key Interfaces
```typescript
// Credit tier type
type CreditType = 'basic' | 'premium' | 'author_publisher';

// Voice option for selection
interface VoiceOption {
  id: string;
  name: string;
  description: string;
  gender: 'male' | 'female' | 'neutral';
  accent: string;
  sampleUrl: string;
}

// Character voice assignment
interface CharacterVoice {
  characterName: string;
  characterDescription?: string;
  selectedVoiceId: string;
  previewUrl: string;
}

// Main preview data structure
interface AudioPreview {
  id: string;
  audiobookId: string;
  creditType: CreditType;
  processingStatus: ProcessingStatus;
  processingProgress?: number;
  basicVoicePreviewUrl?: string;
  characterVoices?: CharacterVoice[];
  availableVoices?: VoiceOption[];
  estimatedCompletionTime?: string;
  errorMessage?: string;
}
```

## Design Guidelines

### Color Scheme
- **Basic:** Blue accent (`text-primary`)
- **Premium:** Purple accent (`text-purple-600`)
- **Author/Publisher:** Blue accent (`text-blue-600`)

### Icons
- Basic: `BookOpen` icon
- Premium: `Sparkles` icon
- Author/Publisher: `Users` icon

### Layout
- Maximum width: 1280px (max-w-6xl)
- Spacing: Consistent 1.5rem (space-y-6)
- Cards: Border-2 with hover effects
- Responsive: Grid layout for multiple items

### Typography
- Page title: 3xl, bold
- Section titles: lg, semibold
- Descriptions: sm, muted-foreground
- Labels: sm, medium

## Routing

The preview page is accessible at:
```
/preview/:previewId
```

Example:
```
/preview/abc123
```

## Usage Example

After a user uploads a file on the Upload page, redirect them to:
```typescript
navigate(`/preview/${previewId}`);
```

## Backend API Summary

All API endpoints needed for this feature:

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/previews/{previewId}` | GET | Fetch preview data |
| `/api/previews/{previewId}/status` | GET | Poll processing status |
| `/api/previews/{previewId}/basic-voice-sample` | GET | Get basic voice audio |
| `/api/previews/{previewId}/character-samples` | GET | Get character voice audios |
| `/api/voices/available` | GET | List available voice options |
| `/api/previews/{previewId}/character-voices` | PUT | Update character voice selection |
| `/api/previews/{previewId}/confirm` | POST | Confirm and start full conversion |

## Future Enhancements

Potential improvements for future iterations:

1. **Voice Comparison:** Side-by-side comparison of different voices for a character
2. **Waveform Visualization:** Visual audio waveform display
3. **Customization Options:** Adjust speed, pitch, or tone
4. **Preview Regeneration:** Regenerate preview with different voice after selection
5. **Save Draft:** Save voice selections without starting conversion
6. **Share Preview:** Share preview link with collaborators
7. **Annotation Tools:** Add timestamps or notes to previews
8. **A/B Testing:** Compare different voice combinations

## Testing Considerations

1. Test all three credit types separately
2. Verify status polling works correctly
3. Test audio playback across browsers
4. Verify voice selection updates in real-time
5. Test error states (failed upload, network errors)
6. Test with multiple characters (5+)
7. Verify responsive design on mobile devices
8. Test audio file CORS configuration

## Accessibility

- Keyboard navigation for all controls
- ARIA labels on audio players
- Screen reader announcements for status changes
- High contrast mode support
- Focus indicators on interactive elements

---

**Created:** December 11, 2025  
**Last Updated:** December 11, 2025  
**Version:** 1.0
