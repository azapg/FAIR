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

export default function RegisterPage() {
  const navigate = useNavigate()
  const { register, loading } = useAuth()
  const { t } = useTranslation()
  const [name, setName] = React.useState('')
  const [email, setEmail] = React.useState('')
  const [password, setPassword] = React.useState('')

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault()
    try {
      await register({ name, email, password })
      navigate('/')
    } catch (err) {
      const axiosError = err as AxiosError<{ detail?: string }>
      const message = axiosError.response?.data?.detail || t('auth.unableToRegister')
      toast.error(t('auth.registrationFailed'), { description: message })
    }
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
