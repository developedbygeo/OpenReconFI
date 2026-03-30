import { screen, waitFor } from '@testing-library/react'
import { renderWithProviders } from '../../../test/render.tsx'
import { ManualMatchPage } from '../_components/ManualMatchPage.tsx'

describe('ManualMatchPage', () => {
  it('renders manual matching title', async () => {
    renderWithProviders(<ManualMatchPage />)

    await waitFor(() => {
      expect(screen.getByText('Manual Matching')).toBeInTheDocument()
    })
  })

  it('shows selection card with create match button', async () => {
    renderWithProviders(<ManualMatchPage />)

    await waitFor(() => {
      expect(screen.getByText('Create Match')).toBeInTheDocument()
    })

    expect(screen.getByText(/Selected Invoice/)).toBeInTheDocument()
    expect(screen.getByText(/Selected Transaction/)).toBeInTheDocument()
  })

  it('shows unmatched invoices and transactions sections', async () => {
    renderWithProviders(<ManualMatchPage />)

    await waitFor(() => {
      expect(screen.getByText('Unmatched Invoices')).toBeInTheDocument()
    })

    expect(screen.getByText('Unmatched Transactions')).toBeInTheDocument()
  })
})
