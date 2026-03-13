import React, {createContext, useCallback, useContext, useEffect, useMemo, useState} from "react";
import api from "@/lib/api";

export enum AuthUserRole {
  USER = 'user',
  INSTRUCTOR = 'instructor',
  ADMIN = 'admin'
}

export type AuthUser = {
  id: string
  name: string
  email: string
  role: AuthUserRole
  capabilities: string[]
  settings: Record<string, unknown>
  isVerified: boolean
}

type LoginInput = { username: string; password: string; remember_me?: boolean }
type RegisterInput = { name: string; email: string; password: string }

type AuthContextValue = {
  user: AuthUser | null
  token: string | null
  isAuthenticated: boolean
  loading: boolean
  login: (input: LoginInput) => Promise<void>
  register: (input: RegisterInput) => Promise<void>
  logout: () => void
  hasCapability: (action: string) => boolean
  setSession: (token: string, user: Partial<AuthUser> & { role?: string, isVerified?: boolean }) => void
}

const AuthContext = createContext<AuthContextValue | null>(null)

const normalizeRole = (role: string): AuthUserRole => {
  if (role === 'student') return AuthUserRole.USER
  if (role === 'professor') return AuthUserRole.INSTRUCTOR
  if (role === AuthUserRole.ADMIN) return AuthUserRole.ADMIN
  if (role === AuthUserRole.INSTRUCTOR) return AuthUserRole.INSTRUCTOR
  return AuthUserRole.USER
}

const normalizeUser = (raw: Partial<AuthUser> & { role?: string, isVerified?: boolean }): AuthUser => ({
  id: raw.id ?? '',
  name: raw.name ?? '',
  email: raw.email ?? '',
  role: normalizeRole(raw.role ?? AuthUserRole.USER),
  capabilities: Array.isArray(raw.capabilities) ? raw.capabilities : [],
  settings:
    raw.settings && typeof raw.settings === 'object' && !Array.isArray(raw.settings)
      ? raw.settings
      : {},
  isVerified: raw.isVerified ?? false,
})

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
            const validatedUser: AuthUser = normalizeUser(userRes.data)
            
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
      // OAuth2 way to pass remember_me flag
      form.append('scope', input.remember_me ? 'remember_me' : '')

      const loginRes = await api.post('/auth/login', form, {
        headers: {'Content-Type': 'application/x-www-form-urlencoded'},
      })

      const accessToken = loginRes.data?.access_token

      if (!accessToken) {
        throw new Error('An error occurred during login')
      }

      persist(accessToken, null)

      const userRes = await api.get('/auth/me')

      const nextUser: AuthUser = normalizeUser(userRes.data)
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
      const user = res.data?.user ? normalizeUser(res.data.user) : undefined
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

  const setSession = useCallback((newToken: string, rawUser: Partial<AuthUser> & { role?: string, isVerified?: boolean }) => {
    const newUser = normalizeUser(rawUser)
    setToken(newToken)
    setUser(newUser)
    persist(newToken, newUser)
  }, [persist])

  const hasCapability = useCallback((action: string) => {
    return !!user?.capabilities?.includes(action)
  }, [user])

  const value = useMemo<AuthContextValue>(() => ({
    user,
    token,
    isAuthenticated: !!token,
    loading,
    login,
    register,
    logout,
    hasCapability,
    setSession,
  }), [user, token, loading, login, register, logout, hasCapability, setSession])

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
