import { screen, waitFor } from '@testing-library/react'
import { renderWithProviders } from '../../../test/render.tsx'
import { VendorListPage } from '../_components/VendorListPage.tsx'

describe('VendorListPage', () => {
  it('renders vendor table', async () => {
    renderWithProviders(<VendorListPage />)

    await waitFor(() => {
      expect(screen.getByText('Vendors')).toBeInTheDocument()
    })

    expect(screen.getByText('Vercel Inc.')).toBeInTheDocument()
    expect(screen.getByText('Hetzner Online')).toBeInTheDocument()
    expect(screen.getByText('Figma Inc.')).toBeInTheDocument()
  })

  it('shows billing cycles', async () => {
    renderWithProviders(<VendorListPage />)

    await waitFor(() => {
      expect(screen.getAllByText('monthly')).toHaveLength(2)
    })

    expect(screen.getByText('annual')).toBeInTheDocument()
  })

  it('shows add vendor button', async () => {
    renderWithProviders(<VendorListPage />)

    await waitFor(() => {
      expect(screen.getByText('Add Vendor')).toBeInTheDocument()
    })
  })
})
