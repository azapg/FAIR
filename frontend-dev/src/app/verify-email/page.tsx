import * as React from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { AxiosError } from 'axios'
import { CheckCircle2, CircleAlert, LoaderCircle } from 'lucide-react'
import { useTranslation } from 'react-i18next'

import api from '@/lib/api'
import { AuthPageShell } from '@/components/auth/auth-page-shell'
import { Button } from '@/components/ui/button'
import { useAuth } from '@/contexts/auth-context'

type VerifyStatus = 'loading' | 'success' | 'error'

export default function VerifyEmailPage() {
  const { t } = useTranslation()
  const [searchParams] = useSearchParams()
  const token = searchParams.get('token') ?? ''
  const { setSession } = useAuth()

  const [status, setStatus] = React.useState<VerifyStatus>('loading')
  const [error, setError] = React.useState<string | null>(null)

  React.useEffect(() => {
    if (!token.trim()) {
      setStatus('error')
      setError(t('auth.invalidVerifyTokenDescription'))
      return
    }

    let active = true
    const verify = async () => {
      try {
        const response = await api.post('/auth/verify-email/confirm', { token })
        if (!active) return
        if (response.data?.access_token && response.data?.user) {
          setSession(response.data.access_token, response.data.user)
        }
        setStatus('success')
      } catch (err) {
        if (!active) return
        const axiosError = err as AxiosError<{ detail?: string }>
        setError(axiosError.response?.data?.detail ?? t('auth.verifyEmailFailed'))
        setStatus('error')
      }
    }

    void verify()
    return () => {
      active = false
    }
  }, [t, token])

  if (status === 'loading') {
    return (
      <AuthPageShell>
        <div className="flex flex-col items-center gap-4 text-center">
          <LoaderCircle className="h-10 w-10 animate-spin text-primary" />
          <h1 className="text-2xl font-bold">{t('auth.verifyingEmailTitle')}</h1>
          <p className="text-sm text-muted-foreground">{t('auth.verifyingEmailDescription')}</p>
        </div>
      </AuthPageShell>
    )
  }

  if (status === 'success') {
    return (
      <AuthPageShell>
        <div className="flex flex-col items-center gap-4 text-center">
          <CheckCircle2 className="h-10 w-10 text-primary" />
          <h1 className="text-2xl font-bold">{t('auth.verifyEmailSuccessTitle')}</h1>
          <p className="text-sm text-muted-foreground">{t('auth.verifyEmailSuccessDescription')}</p>
          <Button asChild className="w-full">
            <Link to="/">Continue</Link>
          </Button>
        </div>
      </AuthPageShell>
    )
  }

  return (
    <AuthPageShell>
      <div className="flex flex-col items-center gap-4 text-center">
        <CircleAlert className="h-10 w-10 text-destructive" />
        <h1 className="text-2xl font-bold">{t('auth.invalidVerifyTokenTitle')}</h1>
        <p className="text-sm text-muted-foreground">{error ?? t('auth.invalidVerifyTokenDescription')}</p>
        <Button asChild variant="outline" className="w-full">
          <Link to="/login">{t('auth.backToLogin')}</Link>
        </Button>
      </div>
    </AuthPageShell>
  )
}
