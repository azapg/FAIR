import { useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'

import { Button } from '@/components/ui/button'
import { Field, FieldDescription, FieldSeparator } from '@/components/ui/field'
import { useSystemConfig } from '@/hooks/use-system-config'
import api from '@/lib/api'

// Google's unmodified multicolor G, kept local to avoid a third-party script.
export function GoogleIcon() {
  return (
    <svg viewBox="0 0 48 48" aria-hidden="true" data-icon="inline-start">
      <path fill="#EA4335" d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5Z" />
      <path fill="#4285F4" d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6C44.4 38.03 46.98 31.87 46.98 24.55Z" />
      <path fill="#FBBC05" d="M10.53 28.59A14.41 14.41 0 0 1 9.77 24c0-1.59.27-3.13.76-4.59l-7.98-6.19A23.87 23.87 0 0 0 0 24c0 3.87.93 7.53 2.56 10.78l7.97-6.19Z" />
      <path fill="#34A853" d="M24 48c6.48 0 11.93-2.13 15.91-5.8l-7.73-6c-2.15 1.45-4.92 2.3-8.18 2.3-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48Z" />
    </svg>
  )
}

export function GoogleSignInButton({ inviteToken, rememberMe = false, disabled = false }: {
  inviteToken?: string; rememberMe?: boolean; disabled?: boolean
}) {
  const { t } = useTranslation()
  const config = useSystemConfig()
  const [pending, setPending] = useState(false)
  const [error, setError] = useState(false)
  const starting = useRef(false)
  if (!config.data?.authentication?.providers.includes('google')) return null

  async function start() {
    if (starting.current) return
    starting.current = true
    setPending(true)
    setError(false)
    try {
      const { data } = await api.post('/auth/oidc/google/start', { inviteToken, rememberMe })
      window.location.assign(data.authorizationUrl)
    } catch {
      setError(true)
      setPending(false)
      starting.current = false
    }
  }

  return (
    <>
      <Field>
        <Button type="button" variant="outline" size="lg" className="w-full" onClick={start}
          disabled={disabled || pending} aria-busy={pending}>
          <GoogleIcon />
          {pending ? t('common.wait') : t('auth.continueWithGoogle')}
        </Button>
        {error && <FieldDescription role="alert">{t('auth.googleErrors.try_again')}</FieldDescription>}
      </Field>
      <FieldSeparator>{t('common.or')}</FieldSeparator>
    </>
  )
}
