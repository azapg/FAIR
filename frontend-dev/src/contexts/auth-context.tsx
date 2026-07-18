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
export type RegisterResult = {
  verificationRequired: boolean
  detail?: string
}

type AuthContextValue = {
  user: AuthUser | null
  isAuthenticated: boolean
  loading: boolean
  login: (input: LoginInput) => Promise<void>
  register: (input: RegisterInput) => Promise<RegisterResult>
  logout: () => Promise<void>
  hasCapability: (action: string) => boolean
  setSession: (user: Partial<AuthUser> & { role?: string, isVerified?: boolean, is_verified?: boolean }) => void
}

const AuthContext = createContext<AuthContextValue | null>(null)

const normalizeRole = (role: string): AuthUserRole => {
  if (role === 'student') return AuthUserRole.USER
  if (role === 'professor') return AuthUserRole.INSTRUCTOR
  if (role === AuthUserRole.ADMIN) return AuthUserRole.ADMIN
  if (role === AuthUserRole.INSTRUCTOR) return AuthUserRole.INSTRUCTOR
  return AuthUserRole.USER
}

const normalizeUser = (raw: Partial<AuthUser> & { role?: string, isVerified?: boolean, is_verified?: boolean }): AuthUser => ({
  id: raw.id ?? '',
  name: raw.name ?? '',
  email: raw.email ?? '',
  role: normalizeRole(raw.role ?? AuthUserRole.USER),
  capabilities: Array.isArray(raw.capabilities) ? raw.capabilities : [],
  settings:
    raw.settings && typeof raw.settings === 'object' && !Array.isArray(raw.settings)
      ? raw.settings
      : {},
  isVerified: raw.isVerified ?? raw.is_verified ?? false,
})

export const AuthProvider = ({ children }: { children: React.ReactNode }) => {
  const [user, setUser] = useState<AuthUser | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let active = true
    const validateSession = async () => {
      try {
        localStorage.removeItem('token')
        localStorage.removeItem('user')
        const userRes = await api.get('/auth/me')
        if (active) setUser(normalizeUser(userRes.data))
      } catch {
        if (active) setUser(null)
      } finally {
        if (active) setLoading(false)
      }
    }

    // Listen for session expiry events from the API interceptor
    const handleSessionExpiry = () => {
      setUser(null)
      setLoading(false)
      if (window.location.pathname !== '/login') window.location.href = '/login'
    }

    if (typeof window !== 'undefined') {
      window.addEventListener('auth:session-expired', handleSessionExpiry)
    }

    void validateSession()

    // Cleanup event listener
    return () => {
      active = false
      if (typeof window !== 'undefined') {
        window.removeEventListener('auth:session-expired', handleSessionExpiry)
      }
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

      await api.post('/auth/login', form, {
        headers: {'Content-Type': 'application/x-www-form-urlencoded'},
      })

      try {
        const userRes = await api.get('/auth/me')
        setUser(normalizeUser(userRes.data))
      } catch (error) {
        await api.post('/auth/logout').catch(() => undefined)
        throw error
      }
    } finally {
      setLoading(false)
    }
  }, [])

  const register = useCallback(async (input: RegisterInput) => {
    setLoading(true)
    try {
      const res = await api.post('/auth/register', input)
      const verificationRequired = Boolean(res.data?.verification_required)
      const user = res.data?.user ? normalizeUser(res.data.user) : undefined
      if (user) {
        setUser(user)
        return { verificationRequired: false, detail: res.data?.detail }
      }
      return { verificationRequired, detail: res.data?.detail }
    } finally {
      setLoading(false)
    }
  }, [])

  const logout = useCallback(async () => {
    setUser(null)
    setLoading(false)
    await api.post('/auth/logout').catch(() => undefined)
  }, [])

  const setSession = useCallback((rawUser: Partial<AuthUser> & { role?: string, isVerified?: boolean, is_verified?: boolean }) => {
    const newUser = normalizeUser(rawUser)
    setUser(newUser)
    setLoading(false)
  }, [])

  const hasCapability = useCallback((action: string) => {
    return !!user?.capabilities?.includes(action)
  }, [user])

  const value = useMemo<AuthContextValue>(() => ({
    user,
    isAuthenticated: !!user,
    loading,
    login,
    register,
    logout,
    hasCapability,
    setSession,
  }), [user, loading, login, register, logout, hasCapability, setSession])

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
