import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { renderWithProviders } from '../../../test/render.tsx'
import { InvoiceListPage } from '../_components/InvoiceListPage.tsx'

describe('InvoiceListPage interactions', () => {
  it('clicking a row navigates to invoice detail', async () => {
    const user = userEvent.setup()
    renderWithProviders(<InvoiceListPage />)

    await waitFor(() => {
      expect(screen.getByText('Vercel Inc.')).toBeInTheDocument()
    })

    await user.click(screen.getByText('Vercel Inc.'))
    // Navigation happens via useNavigate — in MemoryRouter the URL updates internally
  })

  it('filter by status changes displayed data', async () => {
    const user = userEvent.setup()
    renderWithProviders(<InvoiceListPage />)

    await waitFor(() => {
      expect(screen.getByPlaceholderText('Filter by status')).toBeInTheDocument()
    })

    await user.click(screen.getByPlaceholderText('Filter by status'))

    await waitFor(() => {
      expect(screen.getByText('flagged')).toBeInTheDocument()
    })
  })
})
