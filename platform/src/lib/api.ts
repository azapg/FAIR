import axios from 'axios'

const api = axios.create({
  baseURL: 'http://localhost:8000/api',
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

// Response interceptor to handle session expiry
api.interceptors.response.use(
  (response) => response,
  (error) => {
    // Check if the error is due to unauthorized access (401) or forbidden (403)
    if (error.response?.status === 401 || error.response?.status === 403) {
      // Clear the invalid session data from localStorage
      if (typeof window !== 'undefined') {
        localStorage.removeItem('token')
        localStorage.removeItem('user')
        
        // Dispatch a custom event to notify the auth context
        window.dispatchEvent(new CustomEvent('auth:session-expired'))
      }
    }
    return Promise.reject(error)
  }
)

export default api