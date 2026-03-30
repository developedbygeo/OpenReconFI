import { screen, waitFor } from '@testing-library/react'
import { renderWithProviders } from '../../../test/render.tsx'
import { InvoiceListPage } from '../_components/InvoiceListPage.tsx'

describe('InvoiceListPage', () => {
  it('renders invoices table with data', async () => {
    renderWithProviders(<InvoiceListPage />)

    await waitFor(() => {
      expect(screen.getByText('Invoices')).toBeInTheDocument()
    })

    expect(screen.getByText('Vercel Inc.')).toBeInTheDocument()
    expect(screen.getByText('Hetzner Online')).toBeInTheDocument()
    expect(screen.getByText('Figma Inc.')).toBeInTheDocument()
  })

  it('shows invoice dates', async () => {
    renderWithProviders(<InvoiceListPage />)

    await waitFor(() => {
      expect(screen.getByText('Vercel Inc.')).toBeInTheDocument()
    })

    expect(screen.getByText('2026-03-01')).toBeInTheDocument()
    expect(screen.getByText('2026-03-05')).toBeInTheDocument()
    expect(screen.getByText('2026-02-28')).toBeInTheDocument()
  })

  it('shows filter dropdowns', async () => {
    renderWithProviders(<InvoiceListPage />)

    await waitFor(() => {
      expect(screen.getByPlaceholderText('Filter by status')).toBeInTheDocument()
    })

    expect(screen.getByPlaceholderText('Filter by category')).toBeInTheDocument()
  })
})
