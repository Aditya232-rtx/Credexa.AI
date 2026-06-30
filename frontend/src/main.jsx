import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import './index.css'

// Hide splash screen
const splash = document.getElementById('splash-screen')
if (splash) {
  splash.classList.add('hidden')
  setTimeout(() => splash.remove(), 700)
}

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
