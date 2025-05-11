import React from 'react'
import ReactDOM from 'react-dom/client'
import { HashRouter } from 'react-router-dom'
import { I18nextProvider } from 'react-i18next'
import App from './App'
import './index.css'
import i18n from './i18n'

// Enable v7 relative splat path behavior to resolve React Router warning
// @ts-ignore
window.REACT_ROUTER_FUTURE_FLAGS = window.REACT_ROUTER_FUTURE_FLAGS || {};
// @ts-ignore
window.REACT_ROUTER_FUTURE_FLAGS.v7_relativeSplatPath = true;

// Load environment variables from env-config.js if running in Docker
// @ts-ignore
if (window.env) {
  // @ts-ignore
  if (window.env.VITE_API_KEY) process.env.VITE_API_KEY = window.env.VITE_API_KEY;
  // @ts-ignore
  if (window.env.VITE_API_URL) process.env.VITE_API_URL = window.env.VITE_API_URL;
  console.log('Environment loaded from container runtime config');
}

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <HashRouter>
      <I18nextProvider i18n={i18n}>
        <App />
      </I18nextProvider>
    </HashRouter>
  </React.StrictMode>,
) 