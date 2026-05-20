import axios from 'axios'

const API_BASE = import.meta.env.VITE_API_URL || 'https://spotclause-api.onrender.com'

export const api = axios.create({
  baseURL: API_BASE,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Add auth token to requests
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('spotclause-token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Handle 401 responses
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      const url = error.config?.url || ''
      // Don't auto-reload on auth endpoints (login/register) — let UI show the error
      if (!url.includes('/auth/')) {
        localStorage.removeItem('spotclause-token')
        localStorage.removeItem('spotclause-user')
        window.location.reload()
      }
    }
    return Promise.reject(error)
  }
)

// Auth API
export const authApi = {
  register: (email: string, password: string, code: string, name?: string) =>
    api.post('/api/auth/register', { email, password, code, name }),

  login: (email: string, password: string) =>
    api.post('/api/auth/login', { email, password }),

  googleLogin: (token: string) =>
    api.post('/api/auth/google', { token }),

  sendVerifyCode: (email: string) =>
    api.post('/api/auth/verify-email/send', null, { params: { email } }),

  confirmVerifyCode: (email: string, code: string) =>
    api.post('/api/auth/verify-email/confirm', { email, code }),

  getGoogleConfig: () =>
    api.get('/api/auth/google-config'),
}

// Feedback API
export const feedbackApi = {
  submit: (content: string) =>
    api.post('/api/feedback/', { content }),

  list: () =>
    api.get('/api/feedback/'),
}
