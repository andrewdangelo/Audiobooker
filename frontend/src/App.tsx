import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import Home from './pages/Home'
import Dashboard from './pages/Dashboard'
import Upload from './pages/Upload'
import Library from './pages/Library'
import BookDetail from './pages/BookDetail'
import NotFound from './pages/NotFound'
import PlayerDemo from './pages/PlayerDemo'
import PlayerPopout from './pages/PlayerPopout'
import Header from './components/layout/Header'
import Footer from './components/layout/Footer'
import { Toaster } from './components/ui/toaster'
import './App.css'

function App() {
  return (
    <Router>
      <div className="min-h-screen flex flex-col">
        <Routes>
          {/* Pop-out player route - no header/footer for minimal UI */}
          <Route path="/player-popout" element={<PlayerPopout />} />
          
          {/* Main app routes with header/footer */}
          <Route path="*" element={
            <>
              <Header />
              <main className="flex-1">
                <Routes>
                  <Route path="/" element={<Home />} />
                  <Route path="/dashboard" element={<Dashboard />} />
                  <Route path="/upload" element={<Upload />} />
                  <Route path="/library" element={<Library />} />
                  <Route path="/book/:id" element={<BookDetail />} />
                  <Route path="/player-demo" element={<PlayerDemo />} />
                  <Route path="*" element={<NotFound />} />
                </Routes>
              </main>
              <Footer />
              <Toaster />
            </>
          } />
        </Routes>
      </div>
    </Router>
  )
}

export default App
