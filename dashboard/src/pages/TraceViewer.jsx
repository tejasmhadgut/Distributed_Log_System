import { useState, useEffect } from 'react'
import { apiFetch } from '../api'

export default function TraceViewer({ token, initialTraceId }) {
  const [requestId, setRequestId] = useState(initialTraceId || '')
  const [trace, setTrace] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    if (initialTraceId) {
      setRequestId(initialTraceId)
      fetchTrace(initialTraceId)
    }
  }, [initialTraceId])

  async function fetchTrace(id) {
    const target = id || requestId
    if (!target) return
    setLoading(true)
    setError('')
    setTrace(null)
    try {
      const data = await apiFetch(`/traces/${target}`, token)
      setTrace(data)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  function handleSubmit(e) {
    e.preventDefault()
    fetchTrace()
  }

  return (
    <div>
      <div className="page-header">
        <h2>Trace Viewer</h2>
      </div>

      <form onSubmit={handleSubmit} style={{ display: 'flex', gap: '10px', marginBottom: '20px', alignItems: 'flex-end' }}>
        <div style={{ flex: 1 }}>
          <div style={labelStyle}>Request ID</div>
          <input
            value={requestId}
            onChange={e => setRequestId(e.target.value)}
            placeholder="e.g. req-abc-123"
            style={{ width: '100%' }}
            required
          />
        </div>
        <button className="primary" type="submit" disabled={loading}>
          {loading ? 'Loading...' : 'View Trace'}
        </button>
      </form>

      {error && <div className="error-msg">{error}</div>}

      {trace && (
        <div>
          <div style={{
            display: 'flex', gap: '24px', padding: '12px 16px',
            background: '#1e1e2e', border: '1px solid #313244',
            borderRadius: '8px', marginBottom: '16px', flexWrap: 'wrap',
          }}>
            <Stat label="Status" value={trace.status} color={
              trace.status === 'SUCCESS' ? '#a6e3a1'
              : trace.status === 'FAILED' ? '#f38ba8' : '#f9e2af'
            } />
            <Stat label="Total Duration" value={`${trace.total_duration_ms}ms`} />
            <Stat label="Spans" value={trace.total_spans} />
            <Stat label="Errors" value={trace.error_count} color={trace.error_count > 0 ? '#f38ba8' : '#a6e3a1'} />
            <Stat label="Services" value={trace.services_involved?.join(', ')} />
          </div>

          <div style={{ background: '#1e1e2e', border: '1px solid #313244', borderRadius: '8px', overflow: 'hidden' }}>
            <table>
              <thead>
                <tr>
                  <th>Service</th>
                  <th>Level</th>
                  <th>Message</th>
                  <th>Latency</th>
                  <th>Time</th>
                </tr>
              </thead>
              <tbody>
                {trace.spans?.map((span, i) => (
                  <SpanRow key={i} span={span} depth={0} />
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}

function SpanRow({ span, depth }) {
  const [collapsed, setCollapsed] = useState(false)
  const hasChildren = span.children?.length > 0

  return (
    <>
      <tr>
        <td>
          <span style={{ paddingLeft: `${depth * 20}px`, display: 'inline-flex', alignItems: 'center', gap: '6px' }}>
            {hasChildren && (
              <span
                onClick={() => setCollapsed(c => !c)}
                style={{ cursor: 'pointer', color: '#6c7086', fontSize: '10px' }}
              >
                {collapsed ? '▶' : '▼'}
              </span>
            )}
            <span style={{ color: '#cdd6f4' }}>{span.service_name}</span>
          </span>
        </td>
        <td>
          <span style={{
            color: span.log_level === 'ERROR' ? '#f38ba8'
              : span.log_level === 'WARN' ? '#f9e2af' : '#a6e3a1',
            fontSize: '12px', fontWeight: 'bold'
          }}>
            {span.log_level}
          </span>
        </td>
        <td style={{ maxWidth: '400px', wordBreak: 'break-word' }}>{span.message}</td>
        <td style={{ color: span.latency_ms > 500 ? '#f38ba8' : '#6c7086', whiteSpace: 'nowrap' }}>
          {span.latency_ms ? `${span.latency_ms}ms` : '—'}
        </td>
        <td style={{ color: '#6c7086', whiteSpace: 'nowrap' }}>
          {span.timestamp ? new Date(span.timestamp).toLocaleTimeString() : '—'}
        </td>
      </tr>
      {!collapsed && hasChildren && span.children.map((child, i) => (
        <SpanRow key={i} span={child} depth={depth + 1} />
      ))}
    </>
  )
}

function Stat({ label, value, color }) {
  return (
    <div>
      <div style={{ color: '#6c7086', fontSize: '11px', marginBottom: '2px' }}>{label}</div>
      <div style={{ color: color || '#cdd6f4', fontWeight: 'bold', fontSize: '14px' }}>{value}</div>
    </div>
  )
}

const labelStyle = { color: '#6c7086', fontSize: '12px', marginBottom: '4px' }
