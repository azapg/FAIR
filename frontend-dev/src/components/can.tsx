import { ReactNode } from 'react'

import { usePermission } from '@/hooks/use-permission'

type CanProps = {
  I: string
  children: ReactNode
}

export function Can({ I, children }: CanProps) {
  const allowed = usePermission(I)
  if (!allowed) return null
  return <>{children}</>
}

