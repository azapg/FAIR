import axios from 'axios'

const development = import.meta.env.DEV;

let baseURL = '/api'

if (development) {
  baseURL = 'http://localhost:8000/api'
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
    if (error.response?.status === 401) {
      clearAuthData();
    }
    return Promise.reject(error);
  }
)

export default api