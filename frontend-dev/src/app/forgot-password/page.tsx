import * as React from 'react'
import { Link } from 'react-router-dom'
import { AxiosError } from 'axios'
import { toast } from 'sonner'
import { Mail, ArrowLeft, ExternalLink } from 'lucide-react'
import { useTranslation } from 'react-i18next'

import api from '@/lib/api'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Field, FieldDescription, FieldGroup, FieldLabel } from '@/components/ui/field'
import { AuthPageShell } from '@/components/auth/auth-page-shell'

export default function ForgotPasswordPage() {
  const { t } = useTranslation()
  const [email, setEmail] = React.useState('')
  const [submitting, setSubmitting] = React.useState(false)
  const [isSuccess, setIsSuccess] = React.useState(false)

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault()
    setSubmitting(true)
    try {
      await api.post('/auth/forgot-password', { email })
      setIsSuccess(true)
    } catch (err) {
      const axiosError = err as AxiosError<{ detail?: string }>
      toast.error(t('auth.unableToSendReset'), {
        description: axiosError.response?.data?.detail ?? t('auth.tryAgainLater'),
      })
      setSubmitting(false)
    }
  }

  if (isSuccess) {
    return (
      <AuthPageShell>
        <div className="flex flex-col items-center gap-6 text-center">
          <div className="flex h-12 w-12 items-center justify-center rounded-full bg-primary/10 text-primary">
            <Mail className="h-6 w-6" />
          </div>
          
          <div className="space-y-2">
            <h1 className="text-2xl font-bold">{t('auth.checkYourEmail')}</h1>
            <p className="text-sm text-muted-foreground">
              {t('auth.resetLinkSent')} <br />
              <span className="font-medium text-foreground">{email}</span>
            </p>
          </div>

          <div className="flex flex-col w-full gap-2">
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

          <p className="text-sm text-muted-foreground">
            {t('auth.didntReceiveEmail')}
          </p>

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
            <h1 className="text-2xl font-bold">{t('auth.forgotPasswordTitle')}</h1>
            <p className="text-sm text-balance text-muted-foreground">
              {t('auth.forgotPasswordDescription')}
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
              disabled={submitting}
            />
          </Field>
          
          <Field>
            <Button type="submit" disabled={submitting} className="w-full">
              {submitting ? t('common.wait') : t('auth.sendResetMessage')}
            </Button>
          </Field>

          <Field>
            <FieldDescription className="text-center">
              <Link to="/login" className="flex items-center justify-center text-sm underline-offset-4 hover:underline">
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
