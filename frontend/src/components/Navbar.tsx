import { Link, useLocation } from 'react-router-dom'
import ThemeToggle from './ThemeToggle'

interface NavbarProps {
  onLoginClick: () => void
}

export default function Navbar({ onLoginClick }: NavbarProps) {
  const location = useLocation()

  const navItems = [
    { path: '/', label: 'Review' },
    { path: '/compare', label: 'Compare' },
    { path: '/pricing', label: 'Pricing' },
  ]

  return (
    <nav className="navbar">
      <div className="navbar-brand">
        <Link to="/" className="logo">
          <span className="logo-icon">&#9878;</span>
          <span className="logo-text">SpotClause</span>
        </Link>
      </div>
      <div className="navbar-nav">
        {navItems.map(item => (
          <Link
            key={item.path}
            to={item.path}
            className={`nav-link ${location.pathname === item.path ? 'active' : ''}`}
          >
            {item.label}
          </Link>
        ))}
      </div>
      <div className="navbar-actions">
        <ThemeToggle />
        <button className="btn btn-primary" onClick={onLoginClick}>
          Log In
        </button>
      </div>
    </nav>
  )
}
