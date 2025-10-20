// TODO: Implement AudiobookList component
// This component displays a list of audiobooks

export default function AudiobookList() {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      {/* Audiobook cards will be rendered here */}
      <p className="text-muted-foreground">No audiobooks yet</p>
    </div>
  )
}
