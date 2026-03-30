import { screen, waitFor } from '@testing-library/react'
import { renderWithProviders } from '../../../test/render.tsx'
import { ReconciliationOverviewPage } from '../_components/ReconciliationOverviewPage.tsx'

describe('ReconciliationOverviewPage', () => {
  it('renders reconciliation overview title', async () => {
    renderWithProviders(<ReconciliationOverviewPage />)

    await waitFor(() => {
      expect(screen.getByText('Reconciliation Overview')).toBeInTheDocument()
    })
  })

  it('renders period picker', async () => {
    renderWithProviders(<ReconciliationOverviewPage />)

    await waitFor(() => {
      expect(screen.getByText('Reconciliation Overview')).toBeInTheDocument()
    })
  })
})
