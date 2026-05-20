import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { describe, it, expect, vi } from 'vitest'
import { AuditTrailTab } from '../AuditTrailTab'
import type { AuditLog } from '@/types'

const { useAuditTrail } = vi.hoisted(() => ({
  useAuditTrail: vi.fn(),
}))

vi.mock('@/hooks/useAuditTrail', () => ({
  useAuditTrail,
}))

const wrapper = ({ children }: { children: React.ReactNode }) => {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
}

const mockEntry = (overrides = {}): AuditLog => ({
  id: 'audit-1',
  action: 'patients.patient.created',
  resource_type: 'Patient',
  resource_id: 'patient-1',
  user: 'user-1',
  user_name: 'Dr. García',
  details: {
    new: {
      first_name: 'Juan',
      last_name: 'Pérez',
      content_hash: 'abc123def4567890',
    },
  },
  result: 'success',
  ip_address: '192.168.1.100',
  created_at: '2025-01-15T10:00:00Z',
  ...overrides,
})

function setupQuery(data: { results?: AuditLog[]; next?: string | null; previous?: string | null; count?: number } | null) {
  useAuditTrail.mockReturnValue({
    data: data
      ? {
          results: data.results ?? [],
          next: data.next ?? null,
          previous: data.previous ?? null,
          count: data.count ?? data.results?.length ?? 0,
        }
      : undefined,
    isLoading: false,
    isError: false,
    error: null,
  })
}

describe('AuditTrailTab', () => {
  it('renders audit entries from mock data', async () => {
    setupQuery({
      results: [
        mockEntry(),
        mockEntry({
          id: 'audit-2',
          action: 'patients.clinicalnote.created',
          user_name: 'Sistema',
          result: 'success',
          details: { new: { title: 'Nota clínica', content_hash: 'def456abc1237890' } },
        }),
      ],
    })

    render(<AuditTrailTab patientId="patient-1" />, { wrapper })

    await waitFor(() => {
      expect(screen.getByText('Auditoría')).toBeInTheDocument()
    })

    // Should show user names
    expect(screen.getByText('Dr. García')).toBeInTheDocument()
    expect(screen.getByText('Sistema')).toBeInTheDocument()
  })

  it('shows loading state', async () => {
    useAuditTrail.mockReturnValue({
      data: undefined,
      isLoading: true,
      isError: false,
      error: null,
    })

    render(<AuditTrailTab patientId="patient-1" />, { wrapper })

    await waitFor(() => {
      // Loading spinner should be present
      const spinner = document.querySelector('.animate-spin')
      expect(spinner).toBeInTheDocument()
    })
  })

  it('shows empty state when no audit entries exist', async () => {
    setupQuery({ results: [], count: 0 })

    render(<AuditTrailTab patientId="patient-1" />, { wrapper })

    await waitFor(() => {
      expect(screen.getByText('No hay registros de auditoría')).toBeInTheDocument()
    })
  })

  it('toggles expandable details on click', async () => {
    setupQuery({
      results: [mockEntry()],
    })

    render(<AuditTrailTab patientId="patient-1" />, { wrapper })

    await waitFor(() => {
      expect(screen.getByText('Dr. García')).toBeInTheDocument()
    })

    // Click on a row to expand
    const row = screen.getByText('Dr. García').closest('tr')
    expect(row).toBeInTheDocument()
    if (row) {
      fireEvent.click(row)
    }

    // The expanded details should show the formatted text
    await waitFor(() => {
      const preElement = document.querySelector('pre')
      expect(preElement).toBeInTheDocument()
    })
  })

  it('shows error state on API failure', async () => {
    useAuditTrail.mockReturnValue({
      data: undefined,
      isLoading: false,
      isError: true,
      error: new Error('Network error'),
    })

    render(<AuditTrailTab patientId="patient-1" />, { wrapper })

    await waitFor(() => {
      expect(screen.getByText('Error al cargar la auditoría')).toBeInTheDocument()
    })
  })

  it('shows success checkmark and failure X icons', async () => {
    setupQuery({
      results: [
        mockEntry({ id: 'ok-1', result: 'success' }),
        mockEntry({ id: 'fail-1', result: 'failure', user_name: 'Admin' }),
      ],
    })

    render(<AuditTrailTab patientId="patient-1" />, { wrapper })

    await waitFor(() => {
      expect(screen.getByText('Dr. García')).toBeInTheDocument()
      expect(screen.getByText('Admin')).toBeInTheDocument()
    })

    // Check icons exist (lucide renders CheckCircle and XCircle as SVGs)
    const checkIcons = document.querySelectorAll('.text-emerald-600')
    const xIcons = document.querySelectorAll('.text-red-500')
    expect(checkIcons.length).toBeGreaterThan(0)
    expect(xIcons.length).toBeGreaterThan(0)
  })
})
