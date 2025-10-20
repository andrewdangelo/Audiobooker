import { Link } from 'react-router-dom'
import { Button } from '../components/ui/button'

export default function Home() {
  return (
    <div className="container mx-auto px-4 py-16">
      <div className="max-w-3xl mx-auto text-center">
        <h1 className="text-5xl font-bold mb-6">
          Transform PDFs into Audiobooks
        </h1>
        <p className="text-xl text-muted-foreground mb-8">
          Convert your PDF documents into high-quality audiobooks using AI-powered text-to-speech technology.
        </p>
        <div className="flex gap-4 justify-center">
          <Link to="/upload">
            <Button size="lg">Get Started</Button>
          </Link>
          <Link to="/library">
            <Button variant="outline" size="lg">View Library</Button>
          </Link>
        </div>
        
        <div className="mt-16 grid md:grid-cols-3 gap-8">
          <div className="p-6 border rounded-lg">
            <h3 className="text-xl font-semibold mb-2">Easy Upload</h3>
            <p className="text-muted-foreground">
              Simply drag and drop your PDF files to get started
            </p>
          </div>
          <div className="p-6 border rounded-lg">
            <h3 className="text-xl font-semibold mb-2">AI-Powered</h3>
            <p className="text-muted-foreground">
              Natural-sounding voices powered by advanced TTS technology
            </p>
          </div>
          <div className="p-6 border rounded-lg">
            <h3 className="text-xl font-semibold mb-2">Cloud Storage</h3>
            <p className="text-muted-foreground">
              Securely store and access your audiobooks anywhere
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
