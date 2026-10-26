import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

const { post, config } = vi.hoisted(() => ({
  post: vi.fn(), config: { data: { authentication: { providers: ['google'] } } },
}))
vi.mock('@/lib/api', () => ({ default: { post } }))
vi.mock('@/hooks/use-system-config', () => ({ useSystemConfig: () => config }))
vi.mock('react-i18next', () => ({ useTranslation: () => ({ t: (key: string) => ({
  'auth.continueWithGoogle': 'Continue with Google', 'common.wait': 'Please wait', 'common.or': 'or',
  'auth.googleErrors.try_again': 'Google sign-in failed. Please try again.',
}[key] ?? key) }) }))

import { GoogleSignInButton } from './google-sign-in-button'

describe('GoogleSignInButton', () => {
  afterEach(cleanup)
  beforeEach(() => {
    post.mockReset()
    config.data.authentication.providers = ['google']
  })

  it('is absent when the provider is disabled', () => {
    config.data.authentication.providers = []
    render(<GoogleSignInButton />)
    expect(screen.queryByRole('button')).not.toBeInTheDocument()
    expect(screen.queryByText('or')).not.toBeInTheDocument()
  })

  it('works independently of required email/password fields and passes invitation/remember-me', async () => {
    post.mockImplementation(() => new Promise(() => {}))
    const submit = vi.fn((event) => event.preventDefault())
    render(<form onSubmit={submit}><input type="email" required aria-label="Email" />
      <GoogleSignInButton inviteToken="private-invitation" rememberMe />
    </form>)
    const button = screen.getByRole('button', { name: 'Continue with Google' })
    expect(button).toHaveAttribute('type', 'button')
    fireEvent.click(button)
    fireEvent.click(button)
    await waitFor(() => expect(post).toHaveBeenCalledExactlyOnceWith('/auth/oidc/google/start', {
      inviteToken: 'private-invitation', rememberMe: true,
    }))
    expect(submit).not.toHaveBeenCalled()
    expect(button).toBeDisabled()
  })

  it('shows a recoverable error and permits retry', async () => {
    post.mockRejectedValue(new Error('offline'))
    render(<GoogleSignInButton />)
    fireEvent.click(screen.getByRole('button', { name: 'Continue with Google' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Please try again')
    await act(async () => fireEvent.click(screen.getByRole('button', { name: 'Continue with Google' })))
    expect(post).toHaveBeenCalledTimes(2)
  })

  it('respects required invitation and auth loading state', () => {
    render(<GoogleSignInButton disabled />)
    expect(screen.getByRole('button')).toBeDisabled()
  })
})
