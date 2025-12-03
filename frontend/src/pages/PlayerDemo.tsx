/**
 * Audio Player Demo Page
 * 
 * Clean demo page showcasing the AudioPlayer component
 * Documentation available in /docs directory
 */

import AudioPlayer from '@/components/audiobook/AudioPlayer'

export default function PlayerDemo() {
  return (
    <div className="container mx-auto py-8 px-4">
      <AudioPlayer
        audiobookId="demo-123"
        audioUrl="https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3"
        title="The Great Gatsby"
        currentChapter="Chapter 1: In My Younger and More Vulnerable Years"
      />
    </div>
  )
}
