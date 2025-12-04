import { Link } from 'react-router-dom'

export default function Header() {
  return (
    <header className="border-b">
      <div className="container mx-auto px-4 py-4">
        <nav className="flex items-center justify-between">
          <Link to="/" className="text-2xl font-bold">
            Audion
          </Link>
          <div className="flex gap-6">
            <Link to="/dashboard" className="hover:underline">Dashboard</Link>
            <Link to="/upload" className="hover:underline">Upload</Link>
            <Link to="/library" className="hover:underline">Library</Link>
          </div>
        </nav>
      </div>
    </header>
  )
}
