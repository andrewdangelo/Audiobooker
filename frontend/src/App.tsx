import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom'
import Dashboard from './pages/Dashboard'
import Upload from './pages/Upload'
import Library from './pages/Library'
import BookDetail from './pages/BookDetail'
import NotFound from './pages/NotFound'
import PlayerDemo from './pages/PlayerDemo'
import PlayerPopout from './pages/PlayerPopout'
import Login from './pages/Login'
import Signup from './pages/Signup'
import ForgotPassword from './pages/ForgotPassword'
import { AppLayout } from './components/layout/AppLayout'
import './App.css'

function App() {
  return (
    <Router>
      <Routes>
        {/* Auth routes - no sidebar/navbar for clean auth UI */}
        <Route path="/login" element={<Login />} />
        <Route path="/signup" element={<Signup />} />
        <Route path="/forgot-password" element={<ForgotPassword />} />
        
        {/* Pop-out player route - no sidebar/navbar for minimal UI */}
        <Route path="/player-popout" element={<PlayerPopout />} />
        
        {/* Authenticated routes - all use AppLayout with sidebar/navbar */}
        <Route element={<AppLayout />}>
          {/* Default route redirects to dashboard */}
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/library" element={<Library />} />
          <Route path="/book/:id" element={<BookDetail />} />
          <Route path="/upload" element={<Upload />} />
          <Route path="/player-demo" element={<PlayerDemo />} />
          <Route path="*" element={<NotFound />} />
        </Route>
      </Routes>
    </Router>
  )
}

export default App
