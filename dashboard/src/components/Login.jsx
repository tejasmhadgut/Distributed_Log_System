import { useState } from 'react'
import { apiFetch } from '../api'

export default function Login({ onLogin }) {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  async function handleSubmit(e) {
    e.preventDefault()
    setLoading(true)
    setError('')
    try {
      const data = await apiFetch('/auth/login', null, {
        method: 'POST',
        body: JSON.stringify({ username, password }),
      })
      onLogin(data.access_token, username, data.refresh_token)

    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
      <div style={{ background: '#1e1e2e', border: '1px solid #313244', borderRadius: '8px', padding: '32px', width: '320px' }}>
        <h2 style={{ color: '#cdd6f4', marginBottom: '24px', fontSize: '18px' }}>Log Analytics Platform</h2>
        <form onSubmit={handleSubmit}>
          <div style={{ marginBottom: '16px' }}>
            <label style={labelStyle}>Username</label>
            <input
              style={inputStyle}
              value={username}
              onChange={e => setUsername(e.target.value)}
              required
              autoFocus
            />
          </div>
          <div style={{ marginBottom: '16px' }}>
            <label style={labelStyle}>Password</label>
            <input
              type="password"
              style={inputStyle}
              value={password}
              onChange={e => setPassword(e.target.value)}
              required
            />
          </div>
          {error && <div style={{ color: '#f38ba8', fontSize: '13px', marginBottom: '12px' }}>{error}</div>}
          <button type="submit" style={btnStyle} disabled={loading}>
            {loading ? 'Logging in...' : 'Login'}
          </button>
        </form>
      </div>
    </div>
  )
}

const labelStyle = { display: 'block', color: '#6c7086', fontSize: '12px', marginBottom: '6px' }
const inputStyle = {
  width: '100%', padding: '8px 10px', background: '#313244',
  border: '1px solid #45475a', borderRadius: '4px', color: '#cdd6f4',
  fontSize: '14px', outline: 'none',
}
const btnStyle = {
  width: '100%', padding: '10px', background: '#89b4fa',
  border: 'none', borderRadius: '4px', color: '#11111b',
  fontWeight: 'bold', fontSize: '14px', cursor: 'pointer',
}
