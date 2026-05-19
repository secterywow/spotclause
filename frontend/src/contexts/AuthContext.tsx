import { createContext, useState, useEffect, useCallback, type ReactNode } from 'react'
import { api } from '../lib/api'

export interface User {
  id: number
  email: string
  name: string | null
  avatar: string | null
  role: string
  plan: string
}

interface AuthContextType {
  user: User | null
  isLoggedIn: boolean
  isAdmin: boolean
  isReady: boolean
  showLogin: boolean
  setShowLogin: (show: boolean) => void
  login: (token: string, user: User) => void
  logout: () => void
}

export const AuthContext = createContext<AuthContextType>({
  user: null,
  isLoggedIn: false,
  isAdmin: false,
  isReady: false,
  showLogin: false,
  setShowLogin: () => {},
  login: () => {},
  logout: () => {},
})

const TOKEN_KEY = 'spotclause-token'
const USER_KEY = 'spotclause-user'

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [showLogin, setShowLogin] = useState(false)
  const [isReady, setIsReady] = useState(false)

  useEffect(() => {
    const token = localStorage.getItem(TOKEN_KEY)
    const storedUser = localStorage.getItem(USER_KEY)
    if (token && storedUser) {
      try {
        setUser(JSON.parse(storedUser))
      } catch {
        localStorage.removeItem(TOKEN_KEY)
        localStorage.removeItem(USER_KEY)
        setIsReady(true)
        return
      }
      // Refresh user data from server (plan may have changed)
      api.get('/api/auth/me')
        .then(res => {
          const freshUser = res.data as User
          setUser(freshUser)
          localStorage.setItem(USER_KEY, JSON.stringify(freshUser))
        })
        .catch(() => {
          // Token invalid — api interceptor handles cleanup + reload
        })
        .finally(() => {
          setIsReady(true)
        })
    } else {
      setIsReady(true)
    }
  }, [])

  const login = useCallback((token: string, userData: User) => {
    localStorage.setItem(TOKEN_KEY, token)
    localStorage.setItem(USER_KEY, JSON.stringify(userData))
    setUser(userData)
    setShowLogin(false)
  }, [])

  const logout = useCallback(() => {
    localStorage.removeItem(TOKEN_KEY)
    localStorage.removeItem(USER_KEY)
    setUser(null)
  }, [])

  const isLoggedIn = !!user
  const isAdmin = user?.role === 'admin'

  return (
    <AuthContext.Provider value={{ user, isLoggedIn, isAdmin, isReady, showLogin, setShowLogin, login, logout }}>
      {children}
    </AuthContext.Provider>
  )
}
