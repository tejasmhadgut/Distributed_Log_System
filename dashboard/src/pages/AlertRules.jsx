import { useState, useEffect } from 'react'
import { apiFetch } from '../api'

export default function AlertRules({ token }) {
  const [rules, setRules] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState({ service_name: '', metric_type: 'error_rate', threshold: '', enabled: true })
  const [saving, setSaving] = useState(false)

  useEffect(() => { loadRules() }, [])

  async function loadRules() {
    setLoading(true)
    try {
      const data = await apiFetch('/alert_rules', token)
      setRules(data.rules)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  async function handleCreate(e) {
    e.preventDefault()
    setSaving(true)
    try {
      await apiFetch('/alert_rules', token, {
        method: 'POST',
        body: JSON.stringify({ ...form, threshold: parseFloat(form.threshold) }),
      })
      setShowForm(false)
      setForm({ service_name: '', metric_type: 'error_rate', threshold: '', enabled: true })
      await loadRules()
    } catch (err) {
      setError(err.message)
    } finally {
      setSaving(false)
    }
  }

  async function handleToggle(rule) {
    try {
      await apiFetch(`/alert_rules/${rule.rule_id}`, token, {
        method: 'PUT',
        body: JSON.stringify({ enabled: !rule.enabled }),
      })
      await loadRules()
    } catch (err) {
      setError(err.message)
    }
  }

  async function handleDelete(rule_id) {
    if (!confirm('Delete this rule?')) return
    try {
      await apiFetch(`/alert_rules/${rule_id}`, token, { method: 'DELETE' })
      await loadRules()
    } catch (err) {
      setError(err.message)
    }
  }

  return (
    <div>
      <div className="page-header">
        <h2>Alert Rules</h2>
        <button className="primary" onClick={() => setShowForm(f => !f)}>
          {showForm ? 'Cancel' : '+ New Rule'}
        </button>
      </div>

      {showForm && (
        <form onSubmit={handleCreate} style={{
          background: '#1e1e2e', border: '1px solid #313244', borderRadius: '8px',
          padding: '16px', marginBottom: '20px',
          display: 'flex', gap: '12px', flexWrap: 'wrap', alignItems: 'flex-end',
        }}>
          <div>
            <div style={labelStyle}>Service</div>
            <input
              value={form.service_name}
              onChange={e => setForm(f => ({ ...f, service_name: e.target.value }))}
              placeholder="api-gateway"
              required
            />
          </div>
          <div>
            <div style={labelStyle}>Metric</div>
            <select value={form.metric_type} onChange={e => setForm(f => ({ ...f, metric_type: e.target.value }))}>
              <option value="error_rate">error_rate</option>
              <option value="latency_p95">latency_p95</option>
              <option value="error_count">error_count</option>
            </select>
          </div>
          <div>
            <div style={labelStyle}>Threshold</div>
            <input
              type="number"
              value={form.threshold}
              onChange={e => setForm(f => ({ ...f, threshold: e.target.value }))}
              placeholder="10"
              style={{ width: '100px' }}
              required
            />
          </div>
          <button className="primary" type="submit" disabled={saving}>
            {saving ? 'Saving...' : 'Create Rule'}
          </button>
        </form>
      )}

      {error && <div className="error-msg" style={{ marginBottom: '12px' }}>{error}</div>}

      {loading ? (
        <div className="empty-msg">Loading...</div>
      ) : rules.length === 0 ? (
        <div className="empty-msg">No alert rules yet</div>
      ) : (
        <div style={{ background: '#1e1e2e', border: '1px solid #313244', borderRadius: '8px', overflow: 'hidden' }}>
          <table>
            <thead>
              <tr>
                <th>Service</th>
                <th>Metric</th>
                <th>Threshold</th>
                <th>Status</th>
                <th>Created</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {rules.map(rule => (
                <tr key={rule.rule_id}>
                  <td>{rule.service_name}</td>
                  <td style={{ color: '#6c7086' }}>{rule.metric_type}</td>
                  <td>{rule.threshold}{rule.metric_type === 'error_rate' ? '%' : rule.metric_type === 'latency_p95' ? 'ms' : ''}</td>
                  <td>
                    <span style={{
                      color: rule.enabled ? '#a6e3a1' : '#6c7086',
                      fontSize: '12px', fontWeight: 'bold'
                    }}>
                      {rule.enabled ? 'ENABLED' : 'DISABLED'}
                    </span>
                  </td>
                  <td style={{ color: '#6c7086' }}>
                    {rule.created_at ? new Date(rule.created_at).toLocaleDateString() : '—'}
                  </td>
                  <td>
                    <div style={{ display: 'flex', gap: '8px' }}>
                      <button className="secondary" onClick={() => handleToggle(rule)}>
                        {rule.enabled ? 'Disable' : 'Enable'}
                      </button>
                      <button className="danger" onClick={() => handleDelete(rule.rule_id)}>
                        Delete
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

const labelStyle = { color: '#6c7086', fontSize: '12px', marginBottom: '4px' }
