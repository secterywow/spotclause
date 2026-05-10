import { NavLink } from 'react-router-dom'
import ThemeToggle from './ThemeToggle'

interface SidebarProps {
  onLogout: () => void
}

export default function Sidebar({ onLogout }: SidebarProps) {
  const menuItems = [
    { path: '/', label: 'Review', icon: '📄' },
    { path: '/compare', label: 'Compare', icon: '⚖️' },
    { path: '/pricing', label: 'Pricing', icon: '💎' },
    { path: '/contracts', label: 'My Contracts', icon: '📁' },
    { path: '/settings', label: 'Settings', icon: '⚙️' },
  ]

  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <NavLink to="/" className="logo">
          <span className="logo-icon">&#9878;</span>
          <span className="logo-text">SpotClause</span>
        </NavLink>
      </div>

      <nav className="sidebar-nav">
        {menuItems.map(item => (
          <NavLink
            key={item.path}
            to={item.path}
            className={({ isActive }) => `sidebar-link ${isActive ? 'active' : ''}`}
          >
            <span className="sidebar-icon">{item.icon}</span>
            <span className="sidebar-label">{item.label}</span>
          </NavLink>
        ))}
      </nav>

      <div className="sidebar-footer">
        <div className="sidebar-divider" />
        <div className="upgrade-card">
          <span className="upgrade-icon">💎</span>
          <p className="upgrade-text">Upgrade to Pro</p>
          <p className="upgrade-sub">Unlock more reviews</p>
          <NavLink to="/pricing" className="btn btn-outline btn-sm">
            View Plans
          </NavLink>
        </div>
        <div className="sidebar-actions">
          <ThemeToggle />
          <button className="btn btn-ghost btn-sm" onClick={onLogout}>
            Sign Out
          </button>
        </div>
      </div>
    </aside>
  )
}
