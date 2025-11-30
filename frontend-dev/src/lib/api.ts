import axios from 'axios'

let baseURL = '/api'

if (import.meta.env.DEV) {
  baseURL = 'http://localhost:8000/api'
}

export function getApiBaseUrl() {
  return baseURL
}

export function getWebSocketUrl(path: string) {
  if (import.meta.env.DEV) {
    // In dev mode with hot reload, backend runs on :8000
    return `ws://localhost:8000${path}`
  }
  
  // In production or when running "fair serve", use the current location
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const host = window.location.host
  return `${protocol}//${host}${path}`
}

const api = axios.create({
  baseURL,
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
})

api.interceptors.request.use((config) => {
  // TODO: change to cookies
  const token = typeof window !== 'undefined' ? localStorage.getItem('token') : null
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

export const clearAuthData = () => {
  localStorage.removeItem('token')
  localStorage.removeItem('user')

  window.dispatchEvent(new CustomEvent('auth:session-expired'))
}

// Response interceptor to handle session expiry
api.interceptors.response.use(
  (response) => response,
  (error) => {
    // Don't trigger session expiry for auth endpoints (login/register)
    // as 401 there means invalid credentials, not an expired session
    const isAuthEndpoint = error.config?.url?.startsWith('/auth/login') || 
                           error.config?.url?.startsWith('/auth/register')
    if (error.response?.status === 401 && !isAuthEndpoint) {
      clearAuthData();
    }
    return Promise.reject(error);
  }
)

export default api