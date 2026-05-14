import { useState, useEffect } from 'react'
import { useAuth } from '../hooks/useAuth'
import { api } from '../lib/api'

export default function Admin() {
  const { isAdmin } = useAuth()
  const [tab, setTab] = useState<'dashboard' | 'users' | 'pricing' | 'rules'>('dashboard')
  const [data, setData] = useState<any>(null)
  const [users, setUsers] = useState<any[]>([])
  const [pricing, setPricing] = useState<any[]>([])
  const [rules, setRules] = useState<any[]>([])

  useEffect(() => {
    if (!isAdmin) return
    loadDashboard()
    loadUsers()
    loadPricing()
    loadRules()
  }, [isAdmin])

  const loadDashboard = async () => {
    try {
      const res = await api.get('/api/admin/dashboard?user_id=1')
      setData(res.data)
    } catch (err) {
      console.error('Failed to load dashboard', err)
    }
  }

  const loadUsers = async () => {
    try {
      const res = await api.get('/api/admin/users?user_id=1')
      setUsers(res.data.users)
    } catch (err) {
      console.error('Failed to load users', err)
    }
  }

  const loadPricing = async () => {
    try {
      const res = await api.get('/api/admin/pricing?user_id=1')
      setPricing(res.data)
    } catch (err) {
      console.error('Failed to load pricing', err)
    }
  }

  const loadRules = async () => {
    try {
      const res = await api.get('/api/admin/rules?user_id=1')
      setRules(res.data)
    } catch (err) {
      console.error('Failed to load rules', err)
    }
  }

  const handleSeedRules = async () => {
    try {
      await api.post('/api/admin/rules/seed?user_id=1')
      loadRules()
      alert('Rules seeded successfully')
    } catch (err) {
      alert('Failed to seed rules')
    }
  }

  if (!isAdmin) {
    return (
      <div className="page">
        <h1>Access Denied</h1>
        <p>Admin access required.</p>
      </div>
    )
  }

  return (
    <div className="page admin-page">
      <h1>Admin Dashboard</h1>

      <div className="admin-tabs">
        <button className={`tab-btn ${tab === 'dashboard' ? 'active' : ''}`} onClick={() => setTab('dashboard')}>Dashboard</button>
        <button className={`tab-btn ${tab === 'users' ? 'active' : ''}`} onClick={() => setTab('users')}>Users</button>
        <button className={`tab-btn ${tab === 'pricing' ? 'active' : ''}`} onClick={() => setTab('pricing')}>Pricing</button>
        <button className={`tab-btn ${tab === 'rules' ? 'active' : ''}`} onClick={() => setTab('rules')}>Rules</button>
      </div>

      {tab === 'dashboard' && data && (
        <div className="admin-dashboard">
          <div className="stats-grid">
            <div className="stat-card">
              <span className="stat-value">{data.totalUsers}</span>
              <span className="stat-label">Total Users</span>
            </div>
            <div className="stat-card">
              <span className="stat-value">{data.totalContracts}</span>
              <span className="stat-label">Contracts Reviewed</span>
            </div>
            <div className="stat-card">
              <span className="stat-value">{data.activeSubscriptions}</span>
              <span className="stat-label">Active Subscriptions</span>
            </div>
            <div className="stat-card">
              <span className="stat-value">${data.monthlyRevenue}</span>
              <span className="stat-label">Monthly Revenue</span>
            </div>
          </div>

          <h3>Recent Users</h3>
          <table className="admin-table">
            <thead>
              <tr>
                <th>ID</th>
                <th>Email</th>
                <th>Name</th>
                <th>Plan</th>
                <th>Created</th>
              </tr>
            </thead>
            <tbody>
              {data.recentUsers.map((u: any) => (
                <tr key={u.id}>
                  <td>{u.id}</td>
                  <td>{u.email}</td>
                  <td>{u.name || '-'}</td>
                  <td>{u.plan}</td>
                  <td>{new Date(u.createdAt).toLocaleDateString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {tab === 'users' && (
        <div className="admin-users">
          <table className="admin-table">
            <thead>
              <tr>
                <th>ID</th>
                <th>Email</th>
                <th>Name</th>
                <th>Role</th>
                <th>Plan</th>
              </tr>
            </thead>
            <tbody>
              {users.map((u: any) => (
                <tr key={u.id}>
                  <td>{u.id}</td>
                  <td>{u.email}</td>
                  <td>{u.name || '-'}</td>
                  <td>{u.role}</td>
                  <td>{u.plan}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {tab === 'pricing' && (
        <div className="admin-pricing">
          <table className="admin-table">
            <thead>
              <tr>
                <th>Country</th>
                <th>Region</th>
                <th>Currency</th>
                <th>Standard Monthly</th>
                <th>Pro Monthly</th>
              </tr>
            </thead>
            <tbody>
              {pricing.map((p: any) => (
                <tr key={p.country_code}>
                  <td>{p.country_code}</td>
                  <td>{p.region_name}</td>
                  <td>{p.currency}</td>
                  <td>{p.standard_monthly}</td>
                  <td>{p.pro_monthly}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {tab === 'rules' && (
        <div className="admin-rules">
          <button className="btn btn-primary" onClick={handleSeedRules}>Seed Initial Rules</button>
          <table className="admin-table">
            <thead>
              <tr>
                <th>Rule ID</th>
                <th>Title</th>
                <th>Category</th>
                <th>Severity</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {rules.map((r: any) => (
                <tr key={r.rule_id}>
                  <td>{r.rule_id}</td>
                  <td>{r.title}</td>
                  <td>{r.category}</td>
                  <td>{r.severity}</td>
                  <td>{r.is_active ? 'Active' : 'Inactive'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
