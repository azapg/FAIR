import React, {createContext, useCallback, useContext, useEffect, useMemo, useState} from "react";
import api from "@/lib/api";

export enum AuthUserRole {
  STUDENT = 'student',
  PROFESSOR = 'professor',
  ADMIN = 'admin'
}

export type AuthUser = {
  id: string
  name: string
  email: string
  role: AuthUserRole
}

type LoginInput = { username: string; password: string }
type RegisterInput = { name: string; email: string; password: string }

type AuthContextValue = {
  user: AuthUser | null
  token: string | null
  isAuthenticated: boolean
  loading: boolean
  login: (input: LoginInput) => Promise<void>
  register: (input: RegisterInput) => Promise<void>
  logout: () => void
}

const AuthContext = createContext<AuthContextValue | null>(null)

export const AuthProvider = ({ children }: { children: React.ReactNode }) => {
  const [user, setUser] = useState<AuthUser | null>(null)
  const [token, setToken] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const validateStoredSession = async () => {
      try {
        const storedToken = typeof window !== 'undefined' ? localStorage.getItem('token') : null
        const storedUser = typeof window !== 'undefined' ? localStorage.getItem('user') : null
        
        if (storedToken && storedUser) {
          // Set the token temporarily to make the validation request
          setToken(storedToken)
          
          try {
            // Validate the token by making a request to the /auth/me endpoint
            const userRes = await api.get('/auth/me')
            const validatedUser: AuthUser = userRes.data
            
            // If validation succeeds, set both token and user
            setUser(validatedUser)
            persist(storedToken, validatedUser)
          } catch (error) {
            // If validation fails, clear the invalid session
            console.log('Stored session is invalid, clearing...')
            setToken(null)
            setUser(null)
            persist(null, null)
          }
        }
      } catch {
        // If any error occurs during validation, clear the session
        setToken(null)
        setUser(null)
        persist(null, null)
      } finally {
        setLoading(false)
      }
    }

    // Listen for session expiry events from the API interceptor
    const handleSessionExpiry = () => {
      setToken(null)
      setUser(null)
      window.location.href = '/login'
    }

    if (typeof window !== 'undefined') {
      window.addEventListener('auth:session-expired', handleSessionExpiry)
    }

    validateStoredSession()

    // Cleanup event listener
    return () => {
      if (typeof window !== 'undefined') {
        window.removeEventListener('auth:session-expired', handleSessionExpiry)
      }
    }
  }, [])

  const persist = useCallback((nextToken: string | null, nextUser: AuthUser | null) => {
    if (typeof window === 'undefined') return
    if (nextToken) {
      localStorage.setItem('token', nextToken)
    } else {
      localStorage.removeItem('token')
    }

    if (nextUser) {
      localStorage.setItem('user', JSON.stringify(nextUser))
    } else {
      localStorage.removeItem('user')
    }
  }, [])

  const login = useCallback(async (input: LoginInput) => {
    setLoading(true)
    try {
      const form = new URLSearchParams()
      form.append('username', input.username)
      form.append('password', input.password)
      form.append('grant_type', 'password')
      form.append('scope', '')

      const loginRes = await api.post('/auth/login', form, {
        headers: {'Content-Type': 'application/x-www-form-urlencoded'},
      })

      const accessToken = loginRes.data?.access_token

      if (!accessToken) {
        throw new Error('An error occurred during login')
      }

      persist(accessToken, null)

      const userRes = await api.get('/auth/me')

      const nextUser: AuthUser = userRes.data
      setToken(accessToken)
      setUser(nextUser)
      persist(accessToken, nextUser)
    } finally {
      setLoading(false)
    }
  }, [persist])

  const register = useCallback(async (input: RegisterInput) => {
    setLoading(true)
    try {
      const res = await api.post('/auth/register', input)
      const accessToken: string | undefined = res.data?.access_token
      const user: AuthUser | undefined = res.data?.user
      if (accessToken && user) {
        setToken(accessToken)
        setUser(user)
        persist(accessToken, user)
      }
      // TODO: error handling that is also shown in the component
    } finally {
      setLoading(false)
    }
  }, [persist])

  const logout = useCallback(() => {
    setToken(null)
    setUser(null)
    persist(null, null)
  }, [persist])

  const value = useMemo<AuthContextValue>(() => ({
    user,
    token,
    isAuthenticated: !!token,
    loading,
    login,
    register,
    logout,
  }), [user, token, loading, login, register, logout])

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  )
}

export const useAuth = () => {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider')
  }
  return context
}
