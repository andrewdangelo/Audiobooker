// TODO: Implement AudioPlayer component
// This component provides audio playback controls

export default function AudioPlayer() {
  return (
    <div className="bg-card border rounded-lg p-4">
      <audio controls className="w-full">
        {/* Audio source will be set dynamically */}
      </audio>
      <div className="mt-2 text-sm text-muted-foreground">
        <p>No audio loaded</p>
      </div>
    </div>
  )
}
