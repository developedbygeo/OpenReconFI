import { screen, waitFor } from '@testing-library/react'
import { renderWithProviders } from '../../../test/render.tsx'
import { MatchReviewPage } from '../index.tsx'

describe('MatchReviewPage', () => {
  it('renders matches and run button', async () => {
    renderWithProviders(<MatchReviewPage />)

    await waitFor(() => {
      expect(screen.getByText('Match Review')).toBeInTheDocument()
    })

    expect(screen.getByText('Run Matching')).toBeInTheDocument()
  })

  it('shows exception alert for low-confidence matches', async () => {
    renderWithProviders(<MatchReviewPage />)

    await waitFor(() => {
      expect(screen.getByText(/exception\(s\) flagged/)).toBeInTheDocument()
    })
  })
})
