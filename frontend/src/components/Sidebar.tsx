import { NavLink } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import ThemeToggle from './ThemeToggle'
import LanguageSwitcher from './LanguageSwitcher'

interface SidebarProps {
  onLogout: () => void
}

const ReviewIcon = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
    <polyline points="14 2 14 8 20 8" />
    <line x1="9" y1="13" x2="15" y2="13" />
    <line x1="9" y1="17" x2="13" y2="17" />
  </svg>
)

const CompareIcon = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
    <rect x="3" y="4" width="7" height="16" rx="1" />
    <rect x="14" y="4" width="7" height="16" rx="1" />
    <line x1="6" y1="9" x2="7" y2="9" />
    <line x1="17" y1="9" x2="18" y2="9" />
    <line x1="6" y1="13" x2="7" y2="13" />
    <line x1="17" y1="13" x2="18" y2="13" />
  </svg>
)

const ContractsIcon = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
    <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z" />
  </svg>
)

const SettingsIcon = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="12" cy="12" r="3" />
    <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z" />
  </svg>
)

const LogoutIcon = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">
    <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
    <polyline points="16 17 21 12 16 7" />
    <line x1="21" y1="12" x2="9" y2="12" />
  </svg>
)

const DiamondIcon = () => (
  <svg width="44" height="44" viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg" className="diamond-icon">
    <defs>
      <linearGradient id="diamond-top" x1="0" y1="0" x2="1" y2="0">
        <stop offset="0%" stopColor="#fef3c7" />
        <stop offset="50%" stopColor="#fbbf24" />
        <stop offset="100%" stopColor="#f59e0b" />
      </linearGradient>
      <linearGradient id="diamond-left" x1="0" y1="0" x2="1" y2="1">
        <stop offset="0%" stopColor="#fdba74" />
        <stop offset="100%" stopColor="#ea580c" />
      </linearGradient>
      <linearGradient id="diamond-right" x1="1" y1="0" x2="0" y2="1">
        <stop offset="0%" stopColor="#fed7aa" />
        <stop offset="100%" stopColor="#f97316" />
      </linearGradient>
      <linearGradient id="diamond-shine" x1="0" y1="0" x2="1" y2="1">
        <stop offset="0%" stopColor="#ffffff" stopOpacity="0.9" />
        <stop offset="100%" stopColor="#ffffff" stopOpacity="0" />
      </linearGradient>
    </defs>
    {/* Top facets — wider crown so the diamond reads as a brilliant cut, not a long shard */}
    <polygon points="6,24 18,12 46,12 58,24 32,24" fill="url(#diamond-top)" stroke="#b45309" strokeWidth="0.6" />
    <polygon points="18,12 32,24 32,12" fill="#fde68a" stroke="#b45309" strokeWidth="0.6" />
    <polygon points="32,12 32,24 46,12" fill="#fcd34d" stroke="#b45309" strokeWidth="0.6" />
    {/* Bottom facets — shorter pavilion so the apex doesn't elongate the silhouette */}
    <polygon points="6,24 32,24 32,52" fill="url(#diamond-left)" stroke="#9a3412" strokeWidth="0.6" />
    <polygon points="32,24 58,24 32,52" fill="url(#diamond-right)" stroke="#9a3412" strokeWidth="0.6" />
    {/* Inner facet lines */}
    <line x1="18" y1="24" x2="32" y2="52" stroke="#9a3412" strokeWidth="0.5" opacity="0.5" />
    <line x1="46" y1="24" x2="32" y2="52" stroke="#9a3412" strokeWidth="0.5" opacity="0.5" />
    {/* Shine */}
    <polygon points="8,24 16,24 13,30" fill="url(#diamond-shine)" opacity="0.85" />
  </svg>
)

export default function Sidebar({ onLogout }: SidebarProps) {
  const { t } = useTranslation()

  const menuItems = [
    { path: '/', label: t('nav.review'), Icon: ReviewIcon },
    { path: '/compare', label: t('nav.compare'), Icon: CompareIcon },
    { path: '/contracts', label: t('nav.myContracts'), Icon: ContractsIcon },
    { path: '/settings', label: t('nav.settings'), Icon: SettingsIcon },
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
            <span className="sidebar-icon"><item.Icon /></span>
            <span className="sidebar-label">{item.label}</span>
          </NavLink>
        ))}
      </nav>

      <div className="sidebar-footer">
        <div className="upgrade-card">
          <span className="upgrade-icon"><DiamondIcon /></span>
          <p className="upgrade-text">{t('pricing.upgrade')}</p>
          <p className="upgrade-sub">{t('settings.upgradePrompt')}</p>
          <NavLink to="/pricing" className="btn btn-outline btn-sm">
            {t('pricing.getStarted')}
          </NavLink>
        </div>
        <div className="sidebar-actions">
          <LanguageSwitcher />
          <div className="sidebar-actions-row">
            <ThemeToggle />
            <button className="btn-icon-text" onClick={onLogout} title={t('auth.logout')}>
              <LogoutIcon />
              <span>{t('auth.logout')}</span>
            </button>
          </div>
        </div>
      </div>
    </aside>
  )
}
