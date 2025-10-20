// TODO: Implement Library page
// This page displays all audiobooks

import AudiobookList from '../components/audiobook/AudiobookList'

export default function Library() {
  return (
    <div className="container mx-auto px-4 py-8">
      <div className="flex justify-between items-center mb-8">
        <h1 className="text-3xl font-bold">My Library</h1>
        <div className="flex gap-4">
          {/* Add filters and sorting options */}
        </div>
      </div>
      
      <AudiobookList />
    </div>
  )
}
