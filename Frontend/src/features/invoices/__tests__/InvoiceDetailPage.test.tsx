import { screen, waitFor } from '@testing-library/react'
import { Routes, Route } from 'react-router-dom'
import { renderWithProviders } from '../../../test/render.tsx'
import { InvoiceDetailPage } from '../_components/InvoiceDetailPage.tsx'

describe('InvoiceDetailPage', () => {
  it('renders invoice details', async () => {
    renderWithProviders(
      <Routes>
        <Route path="/invoices/:id" element={<InvoiceDetailPage />} />
      </Routes>,
      { route: '/invoices/11111111-1111-1111-1111-111111111111' },
    )

    await waitFor(() => {
      expect(screen.getByText('Vercel Inc.')).toBeInTheDocument()
    })

    expect(screen.getByText('INV-2026-0312')).toBeInTheDocument()
    expect(screen.getByText('2026-03-01')).toBeInTheDocument()
    expect(screen.getByText('pending')).toBeInTheDocument()
  })

  it('shows error for non-existent invoice', async () => {
    renderWithProviders(
      <Routes>
        <Route path="/invoices/:id" element={<InvoiceDetailPage />} />
      </Routes>,
      { route: '/invoices/nonexistent-id' },
    )

    await waitFor(() => {
      expect(screen.getByText('Failed to load invoice.')).toBeInTheDocument()
    })
  })
})
