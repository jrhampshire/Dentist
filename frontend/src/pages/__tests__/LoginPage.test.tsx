import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { LoginPage } from '../LoginPage'

// The OAuth client ids are read from import.meta.env. vitest exposes them via
// the `env` stub on import.meta, which defaults to a permissive empty object.

vi.mock('@/hooks/useAuth', () => ({
  useAuth: () => ({
    login: vi.fn(),
    oauthLogin: vi.fn(),
    isLoading: false,
    error: null,
    clearError: vi.fn(),
  }),
}))

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual<typeof import('react-router-dom')>('react-router-dom')
  return {
    ...actual,
    useNavigate: () => vi.fn(),
  }
})

describe('LoginPage', () => {
  beforeEach(() => {
    vi.resetModules()
  })

  it('renders the email/password login form', () => {
    render(
      <MemoryRouter>
        <LoginPage />
      </MemoryRouter>,
    )

    expect(screen.getByLabelText(/email/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/contraseña/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /iniciar sesión/i })).toBeInTheDocument()
  })

  it('renders OAuth buttons disabled when env vars are not set', () => {
    render(
      <MemoryRouter>
        <LoginPage />
      </MemoryRouter>,
    )

    const googleButton = screen.getByRole('button', { name: /google.*no configurado/i })
    const appleButton = screen.getByRole('button', { name: /apple.*no configurado/i })

    expect(googleButton).toBeDisabled()
    expect(appleButton).toBeDisabled()
  })

  it('shows the create-account link', () => {
    render(
      <MemoryRouter>
        <LoginPage />
      </MemoryRouter>,
    )

    expect(screen.getByRole('link', { name: /crear cuenta/i })).toBeInTheDocument()
  })
})