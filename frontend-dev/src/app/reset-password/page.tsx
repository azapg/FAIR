import * as React from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { AxiosError } from 'axios'
import { ArrowLeft, CheckCircle2, CircleAlert } from 'lucide-react'
import { useTranslation } from 'react-i18next'

import api from '@/lib/api'
import { AuthPageShell } from '@/components/auth/auth-page-shell'
import { Button } from '@/components/ui/button'
import { Field, FieldDescription, FieldGroup, FieldLabel } from '@/components/ui/field'
import { Input } from '@/components/ui/input'

export default function ResetPasswordPage() {
  const { t } = useTranslation()
  const [searchParams] = useSearchParams()
  const token = searchParams.get('token') ?? ''

  const [password, setPassword] = React.useState('')
  const [confirmPassword, setConfirmPassword] = React.useState('')
  const [submitting, setSubmitting] = React.useState(false)
  const [isSuccess, setIsSuccess] = React.useState(false)
  const [error, setError] = React.useState<string | null>(null)

  const invalidToken = token.trim().length === 0

  async function onSubmit(event: React.FormEvent) {
    event.preventDefault()
    if (password !== confirmPassword) {
      setError(t('auth.resetPasswordsMustMatch'))
      return
    }
    setSubmitting(true)
    setError(null)
    try {
      await api.post('/auth/reset-password/confirm', { token, password })
      setIsSuccess(true)
    } catch (err) {
      const axiosError = err as AxiosError<{ detail?: string }>
      setError(axiosError.response?.data?.detail ?? t('auth.resetPasswordFailed'))
      setSubmitting(false)
    }
  }

  if (invalidToken) {
    return (
      <AuthPageShell>
        <div className="flex flex-col items-center gap-4 text-center">
          <CircleAlert className="h-10 w-10 text-destructive" />
          <h1 className="text-2xl font-bold">{t('auth.invalidResetTokenTitle')}</h1>
          <p className="text-sm text-muted-foreground">{t('auth.invalidResetTokenDescription')}</p>
          <Button asChild variant="outline" className="w-full">
            <Link to="/forgot-password">{t('auth.requestNewResetLink')}</Link>
          </Button>
        </div>
      </AuthPageShell>
    )
  }

  if (isSuccess) {
    return (
      <AuthPageShell>
        <div className="flex flex-col items-center gap-4 text-center">
          <CheckCircle2 className="h-10 w-10 text-primary" />
          <h1 className="text-2xl font-bold">{t('auth.resetPasswordSuccessTitle')}</h1>
          <p className="text-sm text-muted-foreground">{t('auth.resetPasswordSuccessDescription')}</p>
          <Button asChild className="w-full">
            <Link to="/login">{t('auth.backToLogin')}</Link>
          </Button>
        </div>
      </AuthPageShell>
    )
  }

  return (
    <AuthPageShell>
      <form onSubmit={onSubmit} className="flex flex-col gap-6">
        <FieldGroup>
          <div className="flex flex-col items-center gap-1 text-center">
            <h1 className="text-2xl font-bold">{t('auth.resetPasswordTitle')}</h1>
            <p className="text-sm text-balance text-muted-foreground">
              {t('auth.resetPasswordDescription')}
            </p>
          </div>
          <Field>
            <FieldLabel htmlFor="new-password">{t('auth.newPassword')}</FieldLabel>
            <Input
              id="new-password"
              type="password"
              autoComplete="new-password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              required
              disabled={submitting}
            />
          </Field>
          <Field>
            <FieldLabel htmlFor="confirm-password">{t('auth.confirmPassword')}</FieldLabel>
            <Input
              id="confirm-password"
              type="password"
              autoComplete="new-password"
              value={confirmPassword}
              onChange={(event) => setConfirmPassword(event.target.value)}
              required
              disabled={submitting}
            />
          </Field>
          {error ? (
            <FieldDescription className="text-center text-destructive">{error}</FieldDescription>
          ) : null}
          <Field>
            <Button type="submit" disabled={submitting} className="w-full">
              {submitting ? t('common.wait') : t('auth.setNewPassword')}
            </Button>
          </Field>
          <Field>
            <FieldDescription className="text-center">
              <Link to="/login" className="inline-flex items-center underline-offset-4 hover:underline">
                <ArrowLeft className="mr-2 h-4 w-4" />
                {t('auth.backToLogin')}
              </Link>
            </FieldDescription>
          </Field>
        </FieldGroup>
      </form>
    </AuthPageShell>
  )
}
