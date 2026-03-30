import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { renderWithProviders } from '../../../test/render.tsx'
import { CollectionPage } from '../_components/CollectionPage.tsx'

describe('CollectionPage interactions', () => {
  it('sync gmail button is clickable', async () => {
    const user = userEvent.setup()
    renderWithProviders(<CollectionPage />)

    await waitFor(() => {
      expect(screen.getByText('Sync Gmail')).toBeInTheDocument()
    })

    const button = screen.getByText('Sync Gmail').closest('button')!
    expect(button).not.toBeDisabled()
    await user.click(button)
  })
})
