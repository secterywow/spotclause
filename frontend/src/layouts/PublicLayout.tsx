import { Outlet } from 'react-router-dom'
import Navbar from '../components/Navbar'
import Footer from '../components/Footer'

interface PublicLayoutProps {
  onLoginClick: () => void
}

export default function PublicLayout({ onLoginClick }: PublicLayoutProps) {
  return (
    <div className="public-layout">
      <Navbar onLoginClick={onLoginClick} />
      <main className="public-main">
        <Outlet />
      </main>
      <Footer />
    </div>
  )
}
