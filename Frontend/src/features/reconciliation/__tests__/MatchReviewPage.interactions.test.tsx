import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { renderWithProviders } from '../../../test/render.tsx'
import { MatchReviewPage } from '../index.tsx'

describe('MatchReviewPage interactions', () => {
  it('run matching button is clickable', async () => {
    const user = userEvent.setup()
    renderWithProviders(<MatchReviewPage />)

    await waitFor(() => {
      expect(screen.getByText('Run Matching')).toBeInTheDocument()
    })

    const button = screen.getByText('Run Matching').closest('button')!
    expect(button).not.toBeDisabled()
    await user.click(button)
  })
})
