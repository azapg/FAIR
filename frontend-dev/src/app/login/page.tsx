import * as React from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { useAuth } from '@/contexts/auth-context'
import { Button } from '@/components/ui/button'
import { Checkbox } from '@/components/ui/checkbox'
import { Field, FieldDescription, FieldGroup, FieldLabel } from '@/components/ui/field'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { toast } from 'sonner'
import { AxiosError } from 'axios'
import { useTranslation } from 'react-i18next'
import { IfSetting } from '@/components/if-setting'
import { AuthPageShell } from '@/components/auth/auth-page-shell'
import api from '@/lib/api'

export default function LoginPage() {
  const navigate = useNavigate()
  const { login, loading } = useAuth()
  const { t } = useTranslation()
  const [email, setEmail] = React.useState('')
  const [password, setPassword] = React.useState('')
  const [rememberMe, setRememberMe] = React.useState(false)
  const [showResendVerification, setShowResendVerification] = React.useState(false)
  const [resendingVerification, setResendingVerification] = React.useState(false)
  const [resendVerificationSent, setResendVerificationSent] = React.useState(false)

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault()
    try {
      await login({ username: email, password, remember_me: rememberMe })
      navigate('/')
    } catch (err) {
      const axiosError = err as AxiosError<{ detail?: string; code?: string }>
      const errorData = axiosError.response?.data
      const message = errorData?.detail || t('auth.unableToLogin')
      const errorCode = errorData?.code
      const isVerificationRequired =
        axiosError.response?.status === 403 && errorCode === 'email_verification_required'
      if (isVerificationRequired) {
        setShowResendVerification(true)
        setResendVerificationSent(false)
      } else {
        setShowResendVerification(false)
      }
      toast.error(t('auth.loginFailed'), { description: message })
    }
  }

  async function onResendVerification() {
    if (!email.trim()) {
      toast.error(t('auth.loginFailed'), { description: t('auth.enterEmailForResend') })
      return
    }
    setResendingVerification(true)
    try {
      await api.post('/auth/resend-verification-request', { email })
      setResendVerificationSent(true)
      toast.success(t('auth.resendVerificationSent'))
    } catch (err) {
      const axiosError = err as AxiosError<{ detail?: string }>
      toast.error(t('auth.unableToResendVerification'), {
        description: axiosError.response?.data?.detail || t('auth.tryAgainLater'),
      })
    } finally {
      setResendingVerification(false)
    }
  }

  return (
    <AuthPageShell>
      <form onSubmit={onSubmit} className="flex flex-col gap-6">
        <FieldGroup>
          <div className="flex flex-col items-center gap-1 text-center">
            <h1 className="text-2xl font-bold">{t('auth.welcomeBack')}</h1>
            <p className="text-sm text-balance text-muted-foreground">
              {t('auth.loginToFair')}
            </p>
          </div>
          <Field>
            <FieldLabel htmlFor="email">{t('auth.email')}</FieldLabel>
            <Input
              id="email"
              type="email"
              inputMode="email"
              autoComplete="email"
              placeholder={t('auth.emailPlaceholder')}
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              disabled={loading}
            />
          </Field>
          <Field>
            <div className="flex items-center">
              <FieldLabel htmlFor="password">{t('auth.password')}</FieldLabel>
              <IfSetting setting="features.emailEnabled" scope="local">
                <Link
                  to="/forgot-password"
                  className="ml-auto text-sm underline-offset-4 hover:underline"
                >
                  {t('auth.forgotPassword')}
                </Link>
              </IfSetting>
            </div>
            <Input
              id="password"
              type="password"
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              disabled={loading}
            />
          </Field>
          <Field>
            <div className="flex items-center gap-2">
              <Checkbox
                id="remember-me"
                checked={rememberMe}
                onCheckedChange={(checked) => setRememberMe(Boolean(checked))}
                disabled={loading}
              />
              <Label htmlFor="remember-me" className="text-sm font-normal cursor-pointer">
                {t('auth.rememberMe')}
              </Label>
            </div>
          </Field>
          <Field>
            <Button type="submit" disabled={loading} className="w-full">
              {loading ? t('common.wait') : t('auth.signIn')}
            </Button>
          </Field>
          {showResendVerification && (
            <Field>
              <div className="rounded-md border border-primary/30 bg-primary/5 p-3 text-sm">
                <p className="mb-3 text-foreground">{t('auth.verifyRequiredLoginHint')}</p>
                <Button
                  type="button"
                  variant="outline"
                  className="w-full"
                  disabled={resendingVerification}
                  onClick={onResendVerification}
                >
                  {resendingVerification ? t('common.wait') : t('auth.resendVerificationAction')}
                </Button>
                {resendVerificationSent && (
                  <p className="mt-2 text-muted-foreground">{t('auth.resendVerificationSentHint')}</p>
                )}
              </div>
            </Field>
          )}
          <Field>
            <FieldDescription className="text-center">
              {t('auth.noAccount')}{' '}
              <Link to="/register" className="underline underline-offset-4">
                {t('auth.createOne')}
              </Link>
            </FieldDescription>
          </Field>
        </FieldGroup>
      </form>
    </AuthPageShell>
  )
}
