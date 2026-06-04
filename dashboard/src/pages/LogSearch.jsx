import { useState } from 'react'
import { apiFetch } from '../api'

export default function LogSearch({ token, onSelectTrace }) {
  const [service, setService] = useState('')
  const [level, setLevel] = useState('')
  const [hours, setHours] = useState(1)
  const [results, setResults] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  async function handleSearch(e) {
    e.preventDefault()
    setLoading(true)
    setError('')
    try {
      const params = new URLSearchParams({ service, hours, limit: 100 })
      if (level) params.append('level', level)
      const data = await apiFetch(`/logs/search?${params}`, token)
      setResults(data.results)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div>
      <div className="page-header">
        <h2>Log Search</h2>
      </div>

      <form onSubmit={handleSearch} style={{ display: 'flex', gap: '10px', marginBottom: '20px', flexWrap: 'wrap', alignItems: 'flex-end' }}>
        <div>
          <div style={labelStyle}>Service *</div>
          <input value={service} onChange={e => setService(e.target.value)} placeholder="api-gateway" required />
        </div>
        <div>
          <div style={labelStyle}>Level</div>
          <select value={level} onChange={e => setLevel(e.target.value)}>
            <option value="">All</option>
            <option>INFO</option>
            <option>WARN</option>
            <option>ERROR</option>
            <option>DEBUG</option>
          </select>
        </div>
        <div>
          <div style={labelStyle}>Last N hours</div>
          <input type="number" value={hours} onChange={e => setHours(e.target.value)} style={{ width: '80px' }} min={1} max={168} />
        </div>
        <button className="primary" type="submit" disabled={loading}>
          {loading ? 'Searching...' : 'Search'}
        </button>
      </form>

      {error && <div className="error-msg">{error}</div>}

      {results !== null && (
        results.length === 0
          ? <div className="empty-msg">No logs found</div>
          : (
            <div style={{ background: '#1e1e2e', border: '1px solid #313244', borderRadius: '8px', overflow: 'hidden' }}>
              <table>
                <thead>
                  <tr>
                    <th>Time</th>
                    <th>Level</th>
                    <th>Service</th>
                    <th>Message</th>
                    <th>Request ID</th>
                    <th>Latency</th>
                  </tr>
                </thead>
                <tbody>
                  {results.map((log, i) => (
                    <tr key={i}>
                      <td style={{ whiteSpace: 'nowrap', color: '#6c7086' }}>
                        {new Date(log.timestamp).toLocaleTimeString()}
                      </td>
                      <td>
                        <span style={{
                          color: log.log_level === 'ERROR' ? '#f38ba8'
                            : log.log_level === 'WARN' ? '#f9e2af'
                            : '#a6e3a1',
                          fontWeight: 'bold', fontSize: '12px'
                        }}>
                          {log.log_level}
                        </span>
                      </td>
                      <td style={{ color: '#6c7086' }}>{log.service_name}</td>
                      <td style={{ maxWidth: '400px', wordBreak: 'break-word' }}>{log.message}</td>
                      <td>
                        {log.request_id
                          ? <span
                              onClick={() => onSelectTrace(log.request_id)}
                              style={{ color: '#89b4fa', cursor: 'pointer', fontFamily: 'monospace', fontSize: '12px' }}
                            >
                              {log.request_id.slice(0, 12)}...
                            </span>
                          : <span style={{ color: '#45475a' }}>—</span>
                        }
                      </td>
                      <td style={{ color: '#6c7086' }}>{log.latency_ms ? `${log.latency_ms}ms` : '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )
      )}
    </div>
  )
}

const labelStyle = { color: '#6c7086', fontSize: '12px', marginBottom: '4px' }
