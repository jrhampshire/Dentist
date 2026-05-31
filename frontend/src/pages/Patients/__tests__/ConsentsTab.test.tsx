import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { describe, it, expect, vi } from 'vitest'
import { ConsentsTab } from '../ConsentsTab'

const { useConsents, useCreateConsent, useSignConsent } = vi.hoisted(() => ({
  useConsents: vi.fn(),
  useCreateConsent: vi.fn(),
  useSignConsent: vi.fn(),
}))

vi.mock('@/hooks/usePatientConsents', () => ({
  useConsents,
  useCreateConsent,
  useSignConsent,
}))

const wrapper = ({ children }: { children: React.ReactNode }) => {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
}

const mockConsent = (overrides = {}) => ({
  id: 'consent-1',
  patient: 'patient-1',
  consent_type: 'general' as const,
  version: '1.0',
  content: 'Consentimiento para tratamiento general',
  signed: false,
  signed_at: null,
  signature_hash: '',
  created_at: '2025-01-15T10:00:00Z',
  ...overrides,
})

function setupQuery(consents: unknown[]) {
  useConsents.mockReturnValue({ data: consents, isLoading: false })
}

function setupMutations() {
  useCreateConsent.mockReturnValue({ mutateAsync: vi.fn().mockResolvedValue({}), isPending: false })
  useSignConsent.mockReturnValue({ mutateAsync: vi.fn().mockResolvedValue({}), isPending: false })
}

describe('ConsentsTab', () => {
  it('renders empty state when no consents exist', async () => {
    setupQuery([])
    setupMutations()

    render(<ConsentsTab patientId="patient-1" />, { wrapper })

    await waitFor(() => {
      expect(screen.getByText('No hay consentimientos registrados')).toBeInTheDocument()
    })
  })

  it('renders consents list with correct data', async () => {
    setupQuery([
      mockConsent(),
      mockConsent({
        id: 'consent-2',
        consent_type: 'data_processing' as const,
        version: '2.0',
        content: 'Autorización para tratamiento de datos personales',
      }),
    ])
    setupMutations()

    render(<ConsentsTab patientId="patient-1" />, { wrapper })

    await waitFor(() => {
      expect(screen.getByText('General')).toBeInTheDocument()
      expect(screen.getByText('Datos Personales')).toBeInTheDocument()
      expect(screen.getByText('v1.0')).toBeInTheDocument()
      expect(screen.getByText('v2.0')).toBeInTheDocument()
    })
  })

  it('shows signed state with Firmado badge', async () => {
    setupQuery([
      mockConsent({
        id: 'consent-3',
        signed: true,
        signed_at: '2025-01-15T12:00:00Z',
      }),
    ])
    setupMutations()

    render(<ConsentsTab patientId="patient-1" />, { wrapper })

    await waitFor(() => {
      expect(screen.getByText('Firmado')).toBeInTheDocument()
      expect(screen.queryByRole('button', { name: 'Firmar' })).not.toBeInTheDocument()
    })
  })

  it('opens create dialog and submits new consent', async () => {
    setupQuery([])
    const mockCreate = vi.fn().mockResolvedValue({})
    useCreateConsent.mockReturnValue({ mutateAsync: mockCreate, isPending: false })
    useSignConsent.mockReturnValue({ mutateAsync: vi.fn(), isPending: false })

    render(<ConsentsTab patientId="patient-1" />, { wrapper })

    fireEvent.click(screen.getByText('Nuevo Consentimiento'))

    // After opening dialog, verify dialog title exists
    await waitFor(() => {
      const dialogTitle = screen.getByRole('dialog')
      expect(dialogTitle).toBeInTheDocument()
    })

    await userEvent.type(screen.getByPlaceholderText('Texto del consentimiento informado...'), 'Contenido del consentimiento')
    fireEvent.click(screen.getByText('Crear consentimiento'))

    await waitFor(() => {
      expect(mockCreate).toHaveBeenCalledWith({
        patientId: 'patient-1',
        data: expect.objectContaining({
          consent_type: 'general',
          content: 'Contenido del consentimiento',
          version: '1.0',
        }),
      })
    })
  })

  it('calls sign mutation when Firmar button clicked', async () => {
    setupQuery([mockConsent({ id: 'consent-5', signed: false })])
    const mockSign = vi.fn().mockResolvedValue({})
    useCreateConsent.mockReturnValue({ mutateAsync: vi.fn(), isPending: false })
    useSignConsent.mockReturnValue({ mutateAsync: mockSign, isPending: false })

    render(<ConsentsTab patientId="patient-1" />, { wrapper })

    await waitFor(() => {
      expect(screen.getByText('Firmar')).toBeInTheDocument()
    })

    fireEvent.click(screen.getByText('Firmar'))

    await waitFor(() => {
      expect(mockSign).toHaveBeenCalledWith({
        patientId: 'patient-1',
        consentId: 'consent-5',
      })
    })
  })

  it('renders Pendiente badge for unsigned consents', async () => {
    setupQuery([mockConsent({ id: 'consent-6', signed: false })])
    setupMutations()

    render(<ConsentsTab patientId="patient-1" />, { wrapper })

    await waitFor(() => {
      expect(screen.getByText('Pendiente')).toBeInTheDocument()
    })
  })

  it('renders WhatsApp consent type correctly', async () => {
    setupQuery([
      mockConsent({
        id: 'consent-7',
        consent_type: 'whatsapp' as const,
        content: 'Autorización WhatsApp',
      }),
    ])
    setupMutations()

    render(<ConsentsTab patientId="patient-1" />, { wrapper })

    await waitFor(() => {
      expect(screen.getByText('WhatsApp')).toBeInTheDocument()
    })
  })
})
