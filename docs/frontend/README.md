# Frontend Documentation

## Audio Player Component

The audio player component provides a complete audiobook playback experience with shadcn/ui design system integration.

### Documentation Files

- **[QUICK_START.md](./QUICK_START.md)** - Get started quickly with the audio player
- **[AUDIO_PLAYER_README.md](./AUDIO_PLAYER_README.md)** - Complete component documentation
- **[AUDIO_PLAYER_COMPLETE.md](./AUDIO_PLAYER_COMPLETE.md)** - Implementation summary

### Quick Reference

#### Demo Page
Visit `/player-demo` to see the audio player in action.

#### Basic Usage
```tsx
import AudioPlayer from '@/components/audiobook/AudioPlayer'

<AudioPlayer
  audiobookId="your-id"
  audioUrl="/audio/file.mp3"
  title="Book Title"
  currentChapter="Chapter 1"
  coverImage="/cover.jpg"
/>
```

#### Features
- ✅ Play/Pause controls
- ✅ Skip forward/backward (30 seconds)
- ✅ Progress bar with seeking
- ✅ Playback speed control (0.5x - 2.0x)
- ✅ Time display (current + remaining)
- ✅ Bookmark functionality (UI ready)
- ✅ Chapter navigation (UI ready)
- ✅ Shadcn/ui design system
- ✅ Fully responsive

#### API Integration Points
All API integration points are documented in the component code:
1. Fetch audio data (`/api/v1/audiobooks/:id`)
2. Save playback progress (`/api/v1/audiobooks/:id/progress`)
3. Bookmarks (`/api/v1/audiobooks/:id/bookmarks`)
4. Chapters (`/api/v1/audiobooks/:id/chapters`)

See [AUDIO_PLAYER_README.md](./AUDIO_PLAYER_README.md) for detailed integration examples.
