import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import { SessionProvider } from './hooks/useSession';
import './index.css';

// SessionProvider wraps App rather than living inside it, because App itself
// consumes the session to decide whether to render the dashboard or the login
// page. A provider inside the component that reads it cannot work.
ReactDOM.createRoot(document.getElementById('root')).render(<React.StrictMode>
    <SessionProvider>
      <App />
    </SessionProvider>
  </React.StrictMode>);
