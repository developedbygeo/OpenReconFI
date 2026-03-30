import { screen, waitFor } from '@testing-library/react'
import { Routes, Route } from 'react-router-dom'
import { renderWithProviders } from '../../../test/render.tsx'
import { VendorDetailPage } from '../_components/VendorDetailPage.tsx'

describe('VendorDetailPage', () => {
  it('renders vendor details and invoices', async () => {
    renderWithProviders(
      <Routes>
        <Route path="/vendors/:id" element={<VendorDetailPage />} />
      </Routes>,
      { route: '/vendors/v-111111-1111-1111-1111-111111111111' },
    )

    await waitFor(() => {
      expect(screen.getByText('Vercel Inc.')).toBeInTheDocument()
    })

    expect(screen.getByText('monthly')).toBeInTheDocument()
    expect(screen.getByText('Invoice History')).toBeInTheDocument()
  })

  it('shows error for non-existent vendor', async () => {
    renderWithProviders(
      <Routes>
        <Route path="/vendors/:id" element={<VendorDetailPage />} />
      </Routes>,
      { route: '/vendors/nonexistent' },
    )

    await waitFor(() => {
      expect(screen.getByText('Failed to load vendor.')).toBeInTheDocument()
    })
  })
})
