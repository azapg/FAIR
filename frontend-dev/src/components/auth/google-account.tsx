import { useState, type FormEvent } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'

import { Button } from '@/components/ui/button'
import { Dialog, DialogTitle, DialogDescription, DialogHeader, DialogFooter } from '@/components/ui/dialog'
import { ResponsiveDialogContent } from '@/components/ui/responsive-dialog'
import { Field, FieldGroup, FieldLabel, FieldDescription } from '@/components/ui/field'
import { Input } from '@/components/ui/input'
import { GoogleIcon } from './google-sign-in-button'
import api from '@/lib/api'
import { useAuth } from '@/contexts/auth-context'

export function useSignInMethods() {
  const { user } = useAuth()
  return useQuery({
    queryKey: ['sign-in-methods', user?.id],
    enabled: !!user?.id,
    queryFn: async (): Promise<{ hasPassword: boolean; providers: string[] }> =>
      (await api.get('/auth/oidc/identities')).data,
    staleTime: 30_000,
  })
}

export function GoogleAccount({ connected }: { connected: boolean }) {
  const { t } = useTranslation()
  const [open, setOpen] = useState(false)
  const [password, setPassword] = useState('')
  const [pending, setPending] = useState(false)
  const [error, setError] = useState(false)

  async function connect(event: FormEvent) {
    event.preventDefault()
    if (pending) return
    setPending(true)
    setError(false)
    try {
      const { data } = await api.post('/auth/oidc/google/link', { currentPassword: password })
      window.location.assign(data.authorizationUrl)
    } catch {
      setError(true)
      setPending(false)
    }
  }

  return (
    <>
      <div className="flex items-center justify-between gap-3">
        <span className="text-sm font-medium">Google</span>
        {connected ? <span className="text-sm text-muted-foreground">{t('auth.googleConnected')}</span> :
          <Button variant="outline" onClick={() => setOpen(true)}><GoogleIcon />{t('auth.connectGoogle')}</Button>}
      </div>
      <Dialog open={open} onOpenChange={(value) => { setOpen(value); setPassword(''); setError(false) }}>
        <ResponsiveDialogContent>
          <DialogHeader>
            <DialogTitle>{t('auth.connectGoogle')}</DialogTitle>
            <DialogDescription>{t('auth.connectGoogleDescription')}</DialogDescription>
          </DialogHeader>
          <form onSubmit={connect}>
            <FieldGroup>
              <Field data-invalid={error || undefined}>
                <FieldLabel htmlFor="google-current-password">{t('auth.currentPassword')}</FieldLabel>
                <Input id="google-current-password" type="password" autoComplete="current-password"
                  value={password} onChange={(e) => setPassword(e.target.value)} required disabled={pending}
                  aria-invalid={error || undefined} aria-describedby={error ? 'google-link-error' : undefined} />
                {error && <FieldDescription id="google-link-error" role="alert">{t('auth.googleLinkFailed')}</FieldDescription>}
              </Field>
              <DialogFooter>
                <Button type="button" variant="outline" disabled={pending} onClick={() => setOpen(false)}>{t('common.cancel')}</Button>
                <Button type="submit" disabled={pending} aria-busy={pending}>
                  {pending ? t('common.wait') : t('auth.continueWithGoogle')}
                </Button>
              </DialogFooter>
            </FieldGroup>
          </form>
        </ResponsiveDialogContent>
      </Dialog>
    </>
  )
}
