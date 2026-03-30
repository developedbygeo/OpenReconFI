import { screen, waitFor } from '@testing-library/react'
import { Routes, Route } from 'react-router-dom'
import { renderWithProviders } from '../../../test/render.tsx'
import { VendorFormPage } from '../_components/VendorFormPage.tsx'

describe('VendorFormPage', () => {
  it('renders new vendor form', async () => {
    renderWithProviders(
      <Routes>
        <Route path="/vendors/new" element={<VendorFormPage />} />
      </Routes>,
      { route: '/vendors/new' },
    )

    await waitFor(() => {
      expect(screen.getByText('New Vendor')).toBeInTheDocument()
    })

    expect(screen.getByText('Create')).toBeInTheDocument()
  })

  it('renders edit vendor form', async () => {
    renderWithProviders(
      <Routes>
        <Route path="/vendors/:id/edit" element={<VendorFormPage />} />
      </Routes>,
      { route: '/vendors/v-111111-1111-1111-1111-111111111111/edit' },
    )

    await waitFor(() => {
      expect(screen.getByText('Edit Vendor')).toBeInTheDocument()
    })

    expect(screen.getByText('Update')).toBeInTheDocument()
  })
})
