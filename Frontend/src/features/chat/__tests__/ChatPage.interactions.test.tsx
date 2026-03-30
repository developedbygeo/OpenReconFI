import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { renderWithProviders } from '../../../test/render.tsx'
import { ChatPage } from '../index.tsx'

describe('ChatPage interactions', () => {
  it('clear button is enabled when messages exist', async () => {
    renderWithProviders(<ChatPage />)

    await waitFor(() => {
      expect(screen.getByText('Clear')).toBeInTheDocument()
    })

    await waitFor(() => {
      expect(screen.getByText('Clear').closest('button')).not.toBeDisabled()
    })
  })

  it('chat input is present and accepts text', async () => {
    const user = userEvent.setup()
    renderWithProviders(<ChatPage />)

    await waitFor(() => {
      expect(screen.getByPlaceholderText(/ask/i)).toBeInTheDocument()
    })

    const input = screen.getByPlaceholderText(/ask/i)
    await user.type(input, 'How much did I spend?')
    expect(input).toHaveValue('How much did I spend?')
  })
})
