import { useState } from 'react'
import { apiFetch } from '../api'

function AlertRow({ alert, token, onResolve }) {
  const [expanded, setExpanded] = useState(false)
  const [resolving, setResolving] = useState(false)
  const hasErrors = alert.recent_errors?.length > 0

  async function handleResolve() {
    setResolving(true)
    try {
      await apiFetch(`/alerts/${alert.alert_id}/resolve`, token, { method: 'PUT' })
      onResolve()
    } catch (e) {
      console.error(e)
    } finally {
      setResolving(false)
    }
  }

  return (
    <div style={{ background: '#313244', borderRadius: '4px', overflow: 'hidden' }}>
      <div style={{
        display: 'grid',
        gridTemplateColumns: '1fr 1fr auto auto auto',
        padding: '8px 12px',
        fontSize: '13px',
        alignItems: 'center',
        gap: '8px',
      }}>
        <span style={{ color: '#cdd6f4' }}>{alert.service_name}</span>
        <span style={{ color: '#6c7086' }}>{alert.metric_type}</span>
        <span style={{ color: '#f38ba8', fontWeight: 'bold' }}>
          {alert.actual_value}{alert.metric_type.includes('rate') ? '%' : ''}
        </span>
        <button
          className="secondary"
          onClick={handleResolve}
          disabled={resolving}
          style={{ whiteSpace: 'nowrap' }}
        >
          {resolving ? '...' : 'Resolve'}
        </button>
        {hasErrors && (
          <span
            onClick={() => setExpanded(e => !e)}
            style={{ color: '#6c7086', fontSize: '11px', cursor: 'pointer', whiteSpace: 'nowrap' }}
          >
            {expanded ? '▲ hide' : '▼ errors'}
          </span>
        )}
      </div>

      {expanded && (
        <div style={{ borderTop: '1px solid #45475a', padding: '8px 12px' }}>
          <div style={{ color: '#6c7086', fontSize: '11px', marginBottom: '6px' }}>
            Recent errors (last 1 hour):
          </div>
          {alert.recent_errors.map((e, i) => (
            <div key={i} style={{
              display: 'grid',
              gridTemplateColumns: 'auto 1fr',
              gap: '10px',
              padding: '4px 0',
              borderBottom: i < alert.recent_errors.length - 1 ? '1px solid #45475a' : 'none',
              fontSize: '12px',
              alignItems: 'start',
            }}>
              <span style={{ color: '#6c7086', whiteSpace: 'nowrap' }}>
                {new Date(e.timestamp).toLocaleTimeString()}
              </span>
              <span style={{ color: '#f38ba8', wordBreak: 'break-word' }}>{e.message}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

export default function AlertsList({ alerts, token, onResolve }) {
  const firing = alerts?.filter(a => a.state === 'FIRING') ?? []

  if (firing.length === 0) {
    return (
      <div style={{
        background: '#1e1e2e', borderRadius: '8px', padding: '16px',
        border: '1px solid #313244', display: 'flex', alignItems: 'center', gap: '8px',
      }}>
        <span style={{ color: '#a6e3a1', fontSize: '14px' }}>✓ No active alerts</span>
      </div>
    )
  }

  return (
    <div style={{ background: '#1e1e2e', borderRadius: '8px', padding: '16px', border: '1px solid #f38ba8' }}>
      <h3 style={{ color: '#f38ba8', margin: '0 0 12px 0', fontSize: '14px' }}>
        Active Alerts ({firing.length})
      </h3>
      <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
        {firing.map(alert => (
          <AlertRow key={alert.alert_id} alert={alert} token={token} onResolve={onResolve} />
        ))}
      </div>
    </div>
  )
}
