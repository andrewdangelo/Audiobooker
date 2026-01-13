import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom'
import Dashboard from './pages/Dashboard'
import Upload from './pages/Upload'
import Library from './pages/Library'
import Store from './pages/Store'
import StoreBookDetail from './pages/StoreBookDetail'
import Cart from './pages/Cart'
import Checkout from './pages/Checkout'
import BookDetail from './pages/BookDetail'
import AudiobookPreview from './pages/AudiobookPreview'
import Pricing from './pages/Pricing'
import Purchase from './pages/Purchase'
import PurchaseSuccess from './pages/PurchaseSuccess'
import NotFound from './pages/NotFound'
import PlayerDemo from './pages/PlayerDemo'
import PlayerPopout from './pages/PlayerPopout'
import Login from './pages/Login'
import Signup from './pages/Signup'
import ForgotPassword from './pages/ForgotPassword'
import Settings from './pages/Settings'
import PermissionsDemo from './pages/PermissionsDemo'
import PublishToStore from './pages/PublishToStore'
import MyListings from './pages/MyListings'
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
          <Route path="/settings" element={<Settings />} />
          <Route path="/permissions-demo" element={<PermissionsDemo />} />
          <Route path="/library" element={<Library />} />
          <Route path="/store" element={<Store />} />
          <Route path="/store/book/:id" element={<StoreBookDetail />} />
          <Route path="/cart" element={<Cart />} />
          <Route path="/checkout" element={<Checkout />} />
          <Route path="/book/:id" element={<BookDetail />} />
          <Route path="/upload" element={<Upload />} />
          <Route path="/publish/:audiobookId" element={<PublishToStore />} />
          <Route path="/my-listings" element={<MyListings />} />
          <Route path="/preview/:previewId" element={<AudiobookPreview />} />
          <Route path="/pricing" element={<Pricing />} />
          <Route path="/purchase" element={<Purchase />} />
          <Route path="/purchase/success" element={<PurchaseSuccess />} />
          <Route path="/player-demo" element={<PlayerDemo />} />
          <Route path="*" element={<NotFound />} />
        </Route>
      </Routes>
    </Router>
  )
}

export default App
