import { render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import { describe, it, expect, vi } from 'vitest'
import { PatientDetailPage } from '../PatientDetailPage'

const { usePatient } = vi.hoisted(() => ({
  usePatient: vi.fn(),
}))

vi.mock('@/hooks/usePatients', () => ({
  usePatient,
  usePatients: vi.fn(),
  useCreatePatient: vi.fn(),
  useUpdatePatient: vi.fn(),
  useDeletePatient: vi.fn(),
}))

vi.mock('../ClinicalNotesTab', () => ({
  ClinicalNotesTab: () => <div data-testid="clinical-notes-tab">ClinicalNotesTab</div>,
}))

vi.mock('../ConsentsTab', () => ({
  ConsentsTab: () => <div data-testid="consents-tab">ConsentsTab</div>,
}))

const wrapper = ({ children }: { children: React.ReactNode }) => {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return (
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={['/patients/test-id']}>
        {children}
      </MemoryRouter>
    </QueryClientProvider>
  )
}

function setupPatient(data: Record<string, unknown> | null, isLoading = false, error: Error | null = null) {
  usePatient.mockReturnValue({ data, isLoading, error })
}

describe('PatientDetailPage', () => {
  it('renders loading state while patient is being fetched', () => {
    setupPatient(null, true)

    render(<PatientDetailPage />, { wrapper })
    // Loading shows spinner, back button is not visible
    const spinner = document.querySelector('.animate-spin')
    expect(spinner).toBeInTheDocument()
  })

  it('renders error state when patient fetch fails', async () => {
    setupPatient(null, false, new Error('Patient not found'))

    render(<PatientDetailPage />, { wrapper })
    await waitFor(() => {
      expect(screen.getByText('Error al cargar el paciente')).toBeInTheDocument()
    })
  })

  it('renders tabs after patient data loads', async () => {
    setupPatient({
      id: 'test-id',
      first_name: 'Juan',
      last_name: 'Pérez',
      phone: '5512345678',
      email: 'juan@example.com',
      curp: 'JUAP900101HDFRNN00',
      date_of_birth: '1990-01-01',
      gender: 'M',
      consent_signed: false,
      whatsapp_opt_in: true,
      email_opt_in: true,
    }, false)

    render(<PatientDetailPage />, { wrapper })

    await waitFor(() => {
      expect(screen.getByText('Información')).toBeInTheDocument()
      expect(screen.getByText('Notas Clínicas')).toBeInTheDocument()
      // Consentimientos appears twice (tab + card title), verify tab exists
      const consentItems = screen.getAllByText('Consentimientos')
      expect(consentItems.length).toBeGreaterThanOrEqual(1)
    })
  })

  it('shows patient personal info in the Info tab', async () => {
    setupPatient({
      id: 'test-id',
      first_name: 'María',
      last_name: 'García',
      phone: '5598765432',
      email: 'maria@example.com',
      curp: 'GACM900202MDFRRL09',
      date_of_birth: '1990-02-02',
      gender: 'F',
      blood_type: 'O+',
      consent_signed: false,
      whatsapp_opt_in: true,
      email_opt_in: true,
    }, false)

    render(<PatientDetailPage />, { wrapper })

    await waitFor(() => {
      // Name appears twice (header + info card row)
      const nameElements = screen.getAllByText('María García')
      expect(nameElements.length).toBeGreaterThanOrEqual(1)
      expect(screen.getByText('O+')).toBeInTheDocument()
    })
  })

  it('switches to clinical notes tab when clicked', async () => {
    setupPatient({
      id: 'test-id',
      first_name: 'Test',
      last_name: 'User',
      phone: '5500000000',
      date_of_birth: '2000-01-01',
      gender: 'M',
      consent_signed: false,
      whatsapp_opt_in: true,
      email_opt_in: true,
    }, false)

    render(<PatientDetailPage />, { wrapper })

    const notesTab = screen.getByText('Notas Clínicas')
    notesTab.click()

    await waitFor(() => {
      expect(screen.getByTestId('clinical-notes-tab')).toBeInTheDocument()
    })
  })

  it('switches to consents tab when clicked', async () => {
    setupPatient({
      id: 'test-id',
      first_name: 'Test',
      last_name: 'User',
      phone: '5500000000',
      date_of_birth: '2000-01-01',
      gender: 'M',
      consent_signed: false,
      whatsapp_opt_in: true,
      email_opt_in: true,
    }, false)

    render(<PatientDetailPage />, { wrapper })

    // Click consents tab (use role-based query to avoid ambiguity)
    const consentsTab = screen.getByRole('tab', { name: /Consentimientos/ })
    consentsTab.click()

    await waitFor(() => {
      expect(screen.getByTestId('consents-tab')).toBeInTheDocument()
    })
  })
})
