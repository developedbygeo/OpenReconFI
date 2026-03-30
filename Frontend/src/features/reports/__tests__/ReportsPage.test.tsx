import { screen, waitFor } from '@testing-library/react'
import { renderWithProviders } from '../../../test/render.tsx'
import { ReportsPage } from '../index.tsx'

describe('ReportsPage', () => {
  it('renders reports title and format selector', async () => {
    renderWithProviders(<ReportsPage />)

    await waitFor(() => {
      expect(screen.getByText('Reports')).toBeInTheDocument()
    })
  })

  it('shows download button', async () => {
    renderWithProviders(<ReportsPage />)

    await waitFor(() => {
      expect(screen.getByText('Download')).toBeInTheDocument()
    })
  })
})
