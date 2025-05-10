import React from 'react'
import ReactDOM from 'react-dom/client'
import { HashRouter } from 'react-router-dom'
import App from './App'
import './index.css'

// Enable v7 relative splat path behavior to resolve React Router warning
// @ts-ignore
window.REACT_ROUTER_FUTURE_FLAGS = window.REACT_ROUTER_FUTURE_FLAGS || {};
// @ts-ignore
window.REACT_ROUTER_FUTURE_FLAGS.v7_relativeSplatPath = true;

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <HashRouter>
      <App />
    </HashRouter>
  </React.StrictMode>,
) 