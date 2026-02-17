import { useAuth } from '@/contexts/auth-context'

export function usePermission(action: string): boolean {
  const { hasCapability } = useAuth()
  return hasCapability(action)
}

