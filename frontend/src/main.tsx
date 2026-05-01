import { StrictMode, Component, type ReactNode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'

interface ErrorBoundaryState {
  hasError: boolean;
}

class ErrorBoundary extends Component<{ children: ReactNode }, ErrorBoundaryState> {
  state: ErrorBoundaryState = { hasError: false };

  static getDerivedStateFromError(): ErrorBoundaryState {
    return { hasError: true };
  }

  componentDidCatch(error: Error, info: React.ErrorInfo) {
    console.error('[ErrorBoundary]', error, info);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div style={{ padding: 40, textAlign: 'center', minHeight: '100vh', display: 'flex', flexDirection: 'column', justifyContent: 'center', alignItems: 'center', gap: 16 }}>
          <h2 style={{ fontSize: 18, fontWeight: 600, color: '#1a1a1a' }}>应用遇到错误</h2>
          <p style={{ color: '#666', fontSize: 14 }}>请刷新页面重试</p>
          <button
            onClick={() => window.location.reload()}
            style={{
              padding: '8px 24px', borderRadius: 8, border: 'none',
              background: '#1677ff', color: '#fff', fontSize: 14,
              cursor: 'pointer', fontWeight: 500,
            }}
          >
            刷新页面
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <ErrorBoundary>
      <App />
    </ErrorBoundary>
  </StrictMode>,
)
