import { useState } from 'react'
import { useWebSocket } from './hooks/useWebSocket'
import Login from './components/Login'
import ServiceCard from './components/ServiceCard'
import AlertsList from './components/AlertsList'
import LogSearch from './pages/LogSearch'
import TraceViewer from './pages/TraceViewer'
import AlertRules from './pages/AlertRules'
import UserManagement from './pages/UserManagement'

const MAX_HISTORY = 20
const TABS = ['Dashboard', 'Logs', 'Traces', 'Rules', 'Users']

export default function App() {
  const [token, setToken] = useState(() => localStorage.getItem('token'))
  const [username, setUsername] = useState(() => localStorage.getItem('username'))
  const [activeTab, setActiveTab] = useState('Dashboard')
  const [serviceHistory, setServiceHistory] = useState({})
  const [traceId, setTraceId] = useState('')

  const { data, status } = useWebSocket(
    token ? 'ws://18.191.36.209:8000/ws/metrics' : null
  )

  function handleLogin(t, u, r) {
    localStorage.setItem('token', t)
    localStorage.setItem('refreshToken', r)
    localStorage.setItem('username', u)
    setToken(t)
    setUsername(u)
  }


  function goToTrace(requestId) {
    setTraceId(requestId)
    setActiveTab('Traces')
  }

  function handleLogout() {
    localStorage.removeItem('token')
    localStorage.removeItem('username')
    setToken(null)
    setUsername(null)
  }

  if (!token) return <Login onLogin={handleLogin} />

  const statusColor = { connected: '#a6e3a1', connecting: '#f9e2af', disconnected: '#f38ba8' }[status]

  return (
    <div className="app">
      <header className="header">
        <h1>Log Analytics Platform</h1>
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '13px' }}>
            <div style={{ width: '8px', height: '8px', borderRadius: '50%', background: statusColor }} />
            <span style={{ color: statusColor }}>{status}</span>
            {data && <span style={{ color: '#6c7086' }}>· {new Date(data.timestamp).toLocaleTimeString()}</span>}
          </div>
          <span style={{ color: '#6c7086', fontSize: '13px' }}>{username}</span>
          <button onClick={handleLogout} style={logoutBtnStyle}>Logout</button>
        </div>
      </header>

      <nav style={{ display: 'flex', gap: '4px', marginBottom: '24px', borderBottom: '1px solid #313244', paddingBottom: '0' }}>
        {TABS.map(tab => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            style={{
              padding: '8px 16px', background: 'none', border: 'none',
              borderBottom: activeTab === tab ? '2px solid #89b4fa' : '2px solid transparent',
              color: activeTab === tab ? '#89b4fa' : '#6c7086',
              cursor: 'pointer', fontSize: '14px',
            }}
          >
            {tab}
          </button>
        ))}
      </nav>

      <main>
        {activeTab === 'Dashboard' && (
          <div className="main">
            <AlertsList alerts={data?.alerts} token={token} onResolve={() => {}} />
            <div className="services-grid">
              {data?.metrics?.length > 0 ? (
                data.metrics.map(service => (
                  <ServiceCard
                    key={service.service_name}
                    service={service}
                    history={serviceHistory[service.service_name] || []}
                  />
                ))
              ) : (
                <div style={{ color: '#6c7086', fontSize: '14px', gridColumn: '1/-1', textAlign: 'center', padding: '40px' }}>
                  {status === 'connected' ? 'Waiting for metrics — ingest some logs first' : 'Connecting...'}
                </div>
              )}
            </div>
          </div>
        )}
        {activeTab === 'Logs'   && <LogSearch token={token} onSelectTrace={goToTrace} />}
        {activeTab === 'Traces' && <TraceViewer token={token} initialTraceId={traceId} />}
        {activeTab === 'Rules'  && <AlertRules token={token} />}
        {activeTab === 'Users'  && <UserManagement token={token} />}
      </main>
    </div>
  )
}

const logoutBtnStyle = {
  padding: '4px 12px', background: 'none', border: '1px solid #45475a',
  borderRadius: '4px', color: '#6c7086', cursor: 'pointer', fontSize: '13px',
}
