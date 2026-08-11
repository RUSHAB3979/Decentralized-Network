import React from 'react';
import ReactDOM from 'react-dom/client';
import DesktopApp from './DesktopApp';
import '../index.css';

// No StrictMode here, unlike src/main.jsx. StrictMode double-invokes effects in
// development, which would open two polling intervals against the pywebview
// bridge and double every nvidia-smi call behind it.
ReactDOM.createRoot(document.getElementById('root')).render(<DesktopApp />);
