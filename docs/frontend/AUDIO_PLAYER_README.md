# Audio Player Component

A comprehensive, production-ready audio player component for audiobook playback, inspired by Audible's interface.

## 🎯 Features

### Current Features
- ✅ Play/Pause controls with large, accessible button
- ✅ Skip forward/backward (30 seconds, configurable)
- ✅ Progress bar with scrubbing/seeking functionality
- ✅ Playback speed control (0.5x - 2.0x)
- ✅ Time display (current time and remaining time)
- ✅ Responsive design with Tailwind CSS
- ✅ Smooth animations and transitions
- ✅ Album/book cover art display
- ✅ Chapter information display

### Ready for API Integration
- 🔌 Bookmark functionality (UI ready, API integration points documented)
- 🔌 Chapter navigation (UI ready, API integration points documented)
- 🔌 Progress saving (periodic sync documented)
- 🔌 Audio file loading from API (fetch pattern documented)

## 📁 File Structure

```
frontend/src/
├── components/
│   ├── audiobook/
│   │   └── AudioPlayer.tsx          # Main audio player component
│   └── ui/
│       ├── slider.tsx                # Slider component (progress bar)
│       ├── dropdown-menu.tsx         # Dropdown menu (speed control)
│       └── button.tsx                # Button component (existing)
├── pages/
│   └── PlayerDemo.tsx                # Demo page for testing
└── types/
    └── audiobook.ts                  # TypeScript interfaces
```

## 🚀 Usage

### Basic Usage

```tsx
import AudioPlayer from '@/components/audiobook/AudioPlayer'

function MyPage() {
  return (
    <AudioPlayer
      audiobookId="abc-123"
      audioUrl="/audio/sample.mp3"
      title="The Great Gatsby"
      currentChapter="Chapter 1"
      coverImage="/covers/gatsby.jpg"
    />
  )
}
```

### Props

| Prop | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `audiobookId` | `string` | No | - | ID for API integration (fetch metadata, save progress) |
| `audioUrl` | `string` | No | - | Direct URL to audio file |
| `title` | `string` | No | `'Untitled Audiobook'` | Book title to display |
| `coverImage` | `string` | No | - | URL to cover art image |
| `currentChapter` | `string` | No | `'Chapter 1'` | Current chapter name |

## 🎨 Design

### Color Scheme
- **Background**: Dark gradient (slate-900 to slate-800)
- **Accent**: Orange/red gradient (inspired by Audible)
- **Text**: White primary, slate-400 secondary
- **Progress bar**: Orange-500

### Layout
- Maximum width: 4xl (56rem)
- Responsive padding and spacing
- Mobile-friendly touch targets
- Accessible ARIA labels

## 🔌 API Integration

The component is designed to work with or without an API. All API integration points are clearly documented in the code.

### Integration Points

#### 1. Fetch Audio Data (Lines 95-100)

```typescript
useEffect(() => {
  if (audiobookId) {
    fetch(`/api/v1/audiobooks/${audiobookId}`)
      .then(res => res.json())
      .then(data => {
        if (audioRef.current) {
          audioRef.current.src = data.audioUrl
        }
      })
  }
}, [audiobookId])
```

#### 2. Save Playback Progress (Lines 205-210)

```typescript
// Save every 30 seconds
if (Math.floor(audioRef.current.currentTime) % 30 === 0) {
  fetch(`/api/v1/audiobooks/${audiobookId}/progress`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ 
      position: audioRef.current.currentTime 
    })
  })
}
```

#### 3. Bookmarks (Lines 215-220)

```typescript
const addBookmark = async () => {
  await fetch(`/api/v1/audiobooks/${audiobookId}/bookmarks`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      position: currentTime,
      chapterName: currentChapter,
      note: '' // Optional user note
    })
  })
}
```

#### 4. Fetch Chapters (Lines 225-230)

```typescript
useEffect(() => {
  if (audiobookId) {
    fetch(`/api/v1/audiobooks/${audiobookId}/chapters`)
      .then(res => res.json())
      .then(chapters => {
        // Set chapters state
        // Enable chapter navigation
      })
  }
}, [audiobookId])
```

## 🧪 Testing

### Using the Demo Page

1. Start the development server:
   ```bash
   cd frontend
   npm run dev
   ```

2. Navigate to the demo page (add route to your router):
   ```tsx
   import PlayerDemo from '@/pages/PlayerDemo'
   
   // In your router config
   <Route path="/player-demo" element={<PlayerDemo />} />
   ```

3. The demo uses a sample audio file from SoundHelix for testing

### Testing with Your Own Audio

1. Place an audio file in `frontend/public/`:
   ```
   frontend/public/sample-audio.mp3
   ```

2. Update the demo page:
   ```tsx
   <AudioPlayer
     audioUrl="/sample-audio.mp3"
     title="Your Book Title"
   />
   ```

## 🎯 Keyboard Controls (Future Enhancement)

The following keyboard shortcuts are planned:

- `Space`: Play/Pause
- `→`: Skip forward 30s
- `←`: Skip back 30s
- `↑`: Increase volume
- `↓`: Decrease volume
- `B`: Add bookmark

## 📱 Mobile Responsiveness

The player is fully responsive and works on:
- Desktop (optimized for large screens)
- Tablets (touch-friendly controls)
- Mobile phones (compact layout)

## 🔧 Customization

### Changing Skip Intervals

Modify the skip functions in `AudioPlayer.tsx`:

```tsx
// Change from 30 to 15 seconds
<Button onClick={() => skipForward(15)}>
  Skip 15s
</Button>
```

### Adding More Playback Speeds

Edit the `playbackSpeeds` array:

```tsx
const playbackSpeeds = [0.5, 0.75, 1.0, 1.25, 1.5, 1.75, 2.0, 2.5]
```

### Custom Styling

The component uses Tailwind CSS classes. Modify colors:

```tsx
// Change accent color from orange to blue
className="bg-blue-500"  // Instead of bg-orange-500
```

## 📝 Code Documentation

Every function and component includes:
- JSDoc comments explaining purpose
- Parameter descriptions
- Usage examples for API integration
- Clear section markers for easy navigation

## 🤝 Pair Programming Notes

The code is structured for easy collaboration:

1. **Clear Sections**: Each logical section is clearly marked with comments
2. **API Integration Points**: All marked with `API Integration Point #N`
3. **TODO Comments**: Actionable items clearly marked
4. **Type Safety**: Full TypeScript support with interfaces
5. **Modular Design**: Easy to extract features into separate hooks/components

## 🐛 Known Limitations

- Chapter navigation UI is present but not functional (needs API)
- Bookmark display is not implemented (only creation)
- Volume control not included (can be added)
- No offline playback support yet

## 🎓 Learning Resources

For understanding the code:

1. **React Hooks**: useState, useRef are used for state management
2. **Audio API**: Native HTML5 Audio element with programmatic control
3. **Radix UI**: For accessible UI components (Slider, DropdownMenu)
4. **Tailwind CSS**: For styling

## 📄 License

Part of the Audiobooker project.

## 👥 Authors

Audiobooker Team

---

**Questions or issues?** Check the inline code comments or contact the team!
