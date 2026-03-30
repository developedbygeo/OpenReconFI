import { screen, waitFor } from '@testing-library/react'
import { renderWithProviders } from '../../../test/render.tsx'
import { DashboardPage } from '../index.tsx'

describe('DashboardPage', () => {
  it('renders dashboard title', async () => {
    renderWithProviders(<DashboardPage />)

    await waitFor(() => {
      expect(screen.getByText('Dashboard')).toBeInTheDocument()
    })
  })

  it('shows missing invoice alerts section', async () => {
    renderWithProviders(<DashboardPage />)

    await waitFor(() => {
      expect(screen.getByText('Missing Invoice Alerts')).toBeInTheDocument()
    })
  })
})
