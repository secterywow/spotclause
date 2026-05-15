import { Outlet } from 'react-router-dom'
import Navbar from '../components/Navbar'
import Footer from '../components/Footer'

interface PublicLayoutProps {
  onLoginClick: () => void
  onRegisterClick: () => void
}

export default function PublicLayout({ onLoginClick, onRegisterClick }: PublicLayoutProps) {
  return (
    <div className="public-layout">
      <Navbar onLoginClick={onLoginClick} onRegisterClick={onRegisterClick} />
      <main className="public-main">
        <Outlet />
      </main>
      <Footer />
    </div>
  )
}
