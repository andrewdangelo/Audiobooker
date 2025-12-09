import React from 'react'
import ReactDOM from 'react-dom/client'
import { StoreProvider } from './store/Provider'
import App from './App.tsx'
import './index.css'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <StoreProvider>
      <App />
    </StoreProvider>
  </React.StrictMode>,
)
