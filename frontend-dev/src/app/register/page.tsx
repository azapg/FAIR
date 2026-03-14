import * as React from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { useAuth } from '@/contexts/auth-context'
import { Button } from '@/components/ui/button'
import { Field, FieldDescription, FieldGroup, FieldLabel } from '@/components/ui/field'
import { Input } from '@/components/ui/input'
import { toast } from 'sonner'
import { AxiosError } from 'axios'
import { useTranslation } from 'react-i18next'
import { AuthPageShell } from '@/components/auth/auth-page-shell'
import { ArrowLeft, ExternalLink, Mail } from 'lucide-react'

export default function RegisterPage() {
  const navigate = useNavigate()
  const { register, loading } = useAuth()
  const { t } = useTranslation()
  const [name, setName] = React.useState('')
  const [email, setEmail] = React.useState('')
  const [password, setPassword] = React.useState('')
  const [verificationRequired, setVerificationRequired] = React.useState(false)
  const [verificationMessage, setVerificationMessage] = React.useState('')

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault()
    try {
      const result = await register({ name, email, password })
      if (result.verificationRequired) {
        setVerificationRequired(true)
        setVerificationMessage(result.detail ?? t('auth.verifyRegistrationDescription'))
        return
      }
      navigate('/')
    } catch (err) {
      const axiosError = err as AxiosError<{ detail?: string }>
      const message = axiosError.response?.data?.detail || t('auth.unableToRegister')
      toast.error(t('auth.registrationFailed'), { description: message })
    }
  }

  if (verificationRequired) {
    return (
      <AuthPageShell>
        <div className="flex flex-col items-center gap-6 text-center">
          <div className="flex h-12 w-12 items-center justify-center rounded-full bg-primary/10 text-primary">
            <Mail className="h-6 w-6" />
          </div>

          <div className="space-y-2">
            <h1 className="text-2xl font-bold">{t('auth.checkYourEmail')}</h1>
            <p className="text-sm text-muted-foreground">
              {verificationMessage} <br />
              <span className="font-medium text-foreground">{email}</span>
            </p>
          </div>

          <div className="flex w-full flex-col gap-2">
            <Button asChild variant="outline" className="w-full">
              <a href="https://mail.google.com" target="_blank" rel="noopener noreferrer">
                {t('auth.openGmail')} <ExternalLink className="ml-2 h-4 w-4" />
              </a>
            </Button>
            <Button asChild variant="outline" className="w-full">
              <a href="https://outlook.live.com" target="_blank" rel="noopener noreferrer">
                {t('auth.openOutlook')} <ExternalLink className="ml-2 h-4 w-4" />
              </a>
            </Button>
            <Button asChild variant="outline" className="w-full">
              <a href="https://mail.yahoo.com" target="_blank" rel="noopener noreferrer">
                {t('auth.openYahoo')} <ExternalLink className="ml-2 h-4 w-4" />
              </a>
            </Button>
            <Button asChild variant="outline" className="w-full">
              <a href="https://mail.proton.me" target="_blank" rel="noopener noreferrer">
                {t('auth.openProton')} <ExternalLink className="ml-2 h-4 w-4" />
              </a>
            </Button>
          </div>

          <p className="text-sm text-muted-foreground">{t('auth.verifyRegistrationHint')}</p>

          <Button asChild variant="ghost" className="w-full">
            <Link to="/login">
              <ArrowLeft className="mr-2 h-4 w-4" />
              {t('auth.backToLogin')}
            </Link>
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
            <h1 className="text-2xl font-bold">{t('auth.welcome')}</h1>
            <p className="text-sm text-balance text-muted-foreground">
              {t('auth.createYourAccount')}
            </p>
          </div>
          <Field>
            <FieldLabel htmlFor="name">{t('auth.name')}</FieldLabel>
            <Input
              id="name"
              type="text"
              autoComplete="name"
              placeholder={t('auth.namePlaceholder')}
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
              disabled={loading}
            />
          </Field>
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
            <FieldLabel htmlFor="password">{t('auth.password')}</FieldLabel>
            <Input
              id="password"
              type="password"
              autoComplete="new-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              disabled={loading}
            />
          </Field>
          <Field>
            <Button type="submit" disabled={loading} className="w-full">
              {loading ? t('common.wait') : t('auth.createAccount')}
            </Button>
          </Field>
          <Field>
            <FieldDescription className="text-center">
              {t('auth.haveAccount')}{' '}
              <Link to="/login" className="underline underline-offset-4">
                {t('auth.signIn')}
              </Link>
            </FieldDescription>
          </Field>
        </FieldGroup>
      </form>
    </AuthPageShell>
  )
}
