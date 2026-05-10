import { NavLink } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import ThemeToggle from './ThemeToggle'
import LanguageSwitcher from './LanguageSwitcher'

interface SidebarProps {
  onLogout: () => void
}

export default function Sidebar({ onLogout }: SidebarProps) {
  const { t } = useTranslation()

  const menuItems = [
    { path: '/', label: t('nav.review'), icon: '📄' },
    { path: '/compare', label: t('nav.compare'), icon: '⚖️' },
    { path: '/pricing', label: t('nav.pricing'), icon: '💎' },
    { path: '/contracts', label: t('nav.myContracts'), icon: '📁' },
    { path: '/settings', label: t('nav.settings'), icon: '⚙️' },
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
          <p className="upgrade-text">{t('pricing.upgrade')}</p>
          <p className="upgrade-sub">{t('settings.upgradePrompt')}</p>
          <NavLink to="/pricing" className="btn btn-outline btn-sm">
            {t('pricing.getStarted')}
          </NavLink>
        </div>
        <div className="sidebar-actions">
          <LanguageSwitcher />
          <ThemeToggle />
          <button className="btn btn-ghost btn-sm" onClick={onLogout}>
            {t('auth.logout')}
          </button>
        </div>
      </div>
    </aside>
  )
}
