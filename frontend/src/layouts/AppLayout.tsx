import { Outlet } from 'react-router-dom'
import Sidebar from '../components/Sidebar'

interface AppLayoutProps {
  onLogout: () => void
}

export default function AppLayout({ onLogout }: AppLayoutProps) {
  return (
    <div className="app-layout">
      <Sidebar onLogout={onLogout} />
      <main className="app-main">
        <Outlet />
      </main>
    </div>
  )
}
