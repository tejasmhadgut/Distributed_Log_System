import { useState, useEffect } from 'react'
import { apiFetch } from '../api'

const ROLES = ['admin', 'user', 'viewer']

export default function UserManagement({ token }) {
  const [users, setUsers] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [editingRole, setEditingRole] = useState(null)
  const [newRole, setNewRole] = useState('')

  useEffect(() => { loadUsers() }, [])

  async function loadUsers() {
    setLoading(true)
    try {
      const data = await apiFetch('/users', token)
      setUsers(data.users)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  async function handleRoleChange(user_id) {
    try {
      await apiFetch(`/users/${user_id}/role`, token, {
        method: 'PUT',
        body: JSON.stringify({ role: newRole }),
      })
      setEditingRole(null)
      await loadUsers()
    } catch (err) {
      setError(err.message)
    }
  }

  async function handleDeactivate(user_id, username) {
    if (!confirm(`Deactivate user "${username}"? They will not be able to log in.`)) return
    try {
      await apiFetch(`/users/${user_id}/deactivate`, token, { method: 'PUT' })
      await loadUsers()
    } catch (err) {
      setError(err.message)
    }
  }

  return (
    <div>
      <div className="page-header">
        <h2>User Management</h2>
      </div>

      {error && <div className="error-msg" style={{ marginBottom: '12px' }}>{error}</div>}

      {loading ? (
        <div className="empty-msg">Loading...</div>
      ) : (
        <div style={{ background: '#1e1e2e', border: '1px solid #313244', borderRadius: '8px', overflow: 'hidden' }}>
          <table>
            <thead>
              <tr>
                <th>Username</th>
                <th>Email</th>
                <th>Role</th>
                <th>Status</th>
                <th>Created</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {users.map(user => (
                <tr key={user.user_id}>
                  <td>{user.username}</td>
                  <td style={{ color: '#6c7086' }}>{user.email}</td>
                  <td>
                    {editingRole === user.user_id ? (
                      <div style={{ display: 'flex', gap: '6px', alignItems: 'center' }}>
                        <select
                          value={newRole}
                          onChange={e => setNewRole(e.target.value)}
                          style={{ padding: '4px 8px' }}
                        >
                          {ROLES.map(r => <option key={r}>{r}</option>)}
                        </select>
                        <button className="primary" style={{ padding: '4px 10px' }} onClick={() => handleRoleChange(user.user_id)}>
                          Save
                        </button>
                        <button className="secondary" onClick={() => setEditingRole(null)}>
                          Cancel
                        </button>
                      </div>
                    ) : (
                      <span style={{
                        color: user.role === 'admin' ? '#cba6f7'
                          : user.role === 'user' ? '#89b4fa' : '#6c7086',
                        fontWeight: 'bold', fontSize: '12px'
                      }}>
                        {user.role.toUpperCase()}
                      </span>
                    )}
                  </td>
                  <td>
                    <span style={{ color: user.is_active ? '#a6e3a1' : '#f38ba8', fontSize: '12px', fontWeight: 'bold' }}>
                      {user.is_active ? 'ACTIVE' : 'INACTIVE'}
                    </span>
                  </td>
                  <td style={{ color: '#6c7086' }}>
                    {user.created_at ? new Date(user.created_at).toLocaleDateString() : '—'}
                  </td>
                  <td>
                    <div style={{ display: 'flex', gap: '8px' }}>
                      {editingRole !== user.user_id && (
                        <button
                          className="secondary"
                          onClick={() => { setEditingRole(user.user_id); setNewRole(user.role) }}
                        >
                          Change Role
                        </button>
                      )}
                      {user.is_active && (
                        <button className="danger" onClick={() => handleDeactivate(user.user_id, user.username)}>
                          Deactivate
                        </button>
                      )}
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
