import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { describe, it, expect, vi } from 'vitest'
import { ClinicalNotesTab } from '../ClinicalNotesTab'

const { useClinicalNotes, useCreateClinicalNote, useSignClinicalNote } = vi.hoisted(() => ({
  useClinicalNotes: vi.fn(),
  useCreateClinicalNote: vi.fn(),
  useSignClinicalNote: vi.fn(),
}))

vi.mock('@/hooks/useClinicalNotes', () => ({
  useClinicalNotes,
  useCreateClinicalNote,
  useSignClinicalNote,
}))

const wrapper = ({ children }: { children: React.ReactNode }) => {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
}

const mockNote = (overrides = {}) => ({
  id: 'note-1',
  patient: 'patient-1',
  note_type: 'evolution' as const,
  title: 'Nota de evolución',
  content: 'Paciente evoluciona favorablemente',
  is_signed: false,
  signature_hash: '',
  author_name: 'Dr. García',
  created_at: '2025-01-15T10:00:00Z',
  updated_at: '2025-01-15T10:00:00Z',
  ...overrides,
})

function setupQuery(notes: unknown[]) {
  useClinicalNotes.mockReturnValue({ data: notes, isLoading: false })
}

function setupMutations() {
  useCreateClinicalNote.mockReturnValue({ mutateAsync: vi.fn().mockResolvedValue({}), isPending: false })
  useSignClinicalNote.mockReturnValue({ mutateAsync: vi.fn().mockResolvedValue({}), isPending: false })
}

describe('ClinicalNotesTab', () => {
  it('renders empty state when no notes exist', async () => {
    setupQuery([])
    setupMutations()

    render(<ClinicalNotesTab patientId="patient-1" />, { wrapper })

    await waitFor(() => {
      expect(screen.getByText('No hay notas clínicas registradas')).toBeInTheDocument()
    })
  })

  it('renders note list with correct data', async () => {
    setupQuery([
      mockNote(),
      mockNote({
        id: 'note-2',
        note_type: 'treatment' as const,
        title: 'Plan de tratamiento',
        content: 'Extracción programada',
        is_signed: true,
        signed_at: '2025-01-15T11:00:00Z',
      }),
    ])
    setupMutations()

    render(<ClinicalNotesTab patientId="patient-1" />, { wrapper })

    await waitFor(() => {
      expect(screen.getByText('Nota de evolución')).toBeInTheDocument()
      expect(screen.getByText('Plan de tratamiento')).toBeInTheDocument()
    })
  })

  it('shows signed state with Firmada badge and lock icon', async () => {
    setupQuery([mockNote({ id: 'note-3', is_signed: true, signed_at: '2025-01-15T12:00:00Z' })])
    setupMutations()

    render(<ClinicalNotesTab patientId="patient-1" />, { wrapper })

    await waitFor(() => {
      expect(screen.getByText('Firmada')).toBeInTheDocument()
      expect(screen.queryByRole('button', { name: 'Firmar' })).not.toBeInTheDocument()
    })
  })

  it('opens create dialog and submits new note', async () => {
    setupQuery([])
    const mockCreate = vi.fn().mockResolvedValue({})
    useCreateClinicalNote.mockReturnValue({ mutateAsync: mockCreate, isPending: false })
    useSignClinicalNote.mockReturnValue({ mutateAsync: vi.fn(), isPending: false })

    render(<ClinicalNotesTab patientId="patient-1" />, { wrapper })

    fireEvent.click(screen.getByText('Nueva Nota'))

    await waitFor(() => {
      expect(screen.getByText('Nueva Nota Clínica')).toBeInTheDocument()
    })

    await userEvent.type(screen.getByLabelText('Título'), 'Mi nueva nota')
    await userEvent.type(screen.getByLabelText('Contenido'), 'Contenido de la nota clínica')
    fireEvent.click(screen.getByText('Crear nota'))

    await waitFor(() => {
      expect(mockCreate).toHaveBeenCalledWith({
        patientId: 'patient-1',
        data: expect.objectContaining({
          note_type: 'evolution',
          title: 'Mi nueva nota',
          content: 'Contenido de la nota clínica',
        }),
      })
    })
  })

  it('calls sign mutation when Firmar button clicked', async () => {
    setupQuery([mockNote({ id: 'note-5', is_signed: false })])
    const mockSign = vi.fn().mockResolvedValue({})
    useCreateClinicalNote.mockReturnValue({ mutateAsync: vi.fn(), isPending: false })
    useSignClinicalNote.mockReturnValue({ mutateAsync: mockSign, isPending: false })

    render(<ClinicalNotesTab patientId="patient-1" />, { wrapper })

    await waitFor(() => {
      expect(screen.getByText('Firmar')).toBeInTheDocument()
    })

    fireEvent.click(screen.getByText('Firmar'))

    await waitFor(() => {
      expect(mockSign).toHaveBeenCalledWith({
        patientId: 'patient-1',
        noteId: 'note-5',
      })
    })
  })
})
