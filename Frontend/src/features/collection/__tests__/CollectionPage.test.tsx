import { screen, waitFor } from '@testing-library/react'
import { renderWithProviders } from '../../../test/render.tsx'
import { CollectionPage } from '../_components/CollectionPage.tsx'

describe('CollectionPage', () => {
  it('renders job history', async () => {
    renderWithProviders(<CollectionPage />)

    await waitFor(() => {
      expect(screen.getByText('Job History')).toBeInTheDocument()
    })

    await waitFor(() => {
      expect(screen.getByText('done')).toBeInTheDocument()
    })

    expect(screen.getByText('failed')).toBeInTheDocument()
  })

  it('shows sync button', async () => {
    renderWithProviders(<CollectionPage />)

    await waitFor(() => {
      expect(screen.getByText('Sync Gmail')).toBeInTheDocument()
    })
  })
})
