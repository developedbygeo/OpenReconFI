import { screen, waitFor } from '@testing-library/react'
import { renderWithProviders } from '../../../test/render.tsx'
import { ChatPage } from '../index.tsx'

describe('ChatPage', () => {
  it('renders chat history', async () => {
    renderWithProviders(<ChatPage />)

    await waitFor(() => {
      expect(screen.getByText('Expense Chat')).toBeInTheDocument()
    })

    expect(screen.getByText('What are my top 5 vendors by spend?')).toBeInTheDocument()
  })

  it('shows clear button', async () => {
    renderWithProviders(<ChatPage />)

    await waitFor(() => {
      expect(screen.getByText('Clear')).toBeInTheDocument()
    })
  })

  it('renders assistant messages with markdown', async () => {
    renderWithProviders(<ChatPage />)

    await waitFor(() => {
      expect(screen.getByText(/Vercel Inc/)).toBeInTheDocument()
    })
  })
})
