import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { IntegrationsTab } from '../IntegrationsTab'

// Mock the WhatsApp status hook so we can assert the card renders real status
// without wiring up a full React Query provider.
vi.mock('@/hooks/useWhatsAppStatus', () => ({
  useWhatsAppStatus: () => ({
    isConnected: false,
    isLoading: false,
  }),
}))

describe('IntegrationsTab', () => {
  it('renders the WhatsApp card with a Desconectado status', () => {
    render(<IntegrationsTab />)

    expect(screen.getByText('WhatsApp')).toBeInTheDocument()
    expect(screen.getByText('Desconectado')).toBeInTheDocument()
  })

  it('renders Google Calendar and Gmail cards as not available', () => {
    render(<IntegrationsTab />)

    expect(screen.getByText('Google Calendar')).toBeInTheDocument()
    expect(screen.getByText('Gmail')).toBeInTheDocument()

    // Both genuinely-not-implemented integrations expose a disabled button.
    const unavailableButtons = screen.getAllByRole('button', { name: /no disponible/i })
    // Google Calendar + Gmail — WhatsApp button is also disabled but shows no text
    expect(unavailableButtons.length).toBeGreaterThanOrEqual(2)
  })

  it('does not render the misleading "próxima actualización" notice', () => {
    render(<IntegrationsTab />)

    expect(screen.queryByText(/próxima actualización/i)).not.toBeInTheDocument()
  })
})