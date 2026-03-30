import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { renderWithProviders } from '../../../test/render.tsx'
import { VendorListPage } from '../_components/VendorListPage.tsx'

describe('VendorListPage interactions', () => {
  it('clicking a vendor row navigates', async () => {
    const user = userEvent.setup()
    renderWithProviders(<VendorListPage />)

    await waitFor(() => {
      expect(screen.getByText('Vercel Inc.')).toBeInTheDocument()
    })

    await user.click(screen.getByText('Vercel Inc.'))
  })

  it('clicking add vendor navigates to form', async () => {
    const user = userEvent.setup()
    renderWithProviders(<VendorListPage />)

    await waitFor(() => {
      expect(screen.getByText('Add Vendor')).toBeInTheDocument()
    })

    await user.click(screen.getByText('Add Vendor'))
  })
})
