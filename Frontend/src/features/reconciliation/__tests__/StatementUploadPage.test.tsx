import { screen, waitFor } from '@testing-library/react'
import { renderWithProviders } from '../../../test/render.tsx'
import { StatementUploadPage } from '../_components/StatementUploadPage.tsx'

describe('StatementUploadPage', () => {
  it('renders upload title and supported formats', async () => {
    renderWithProviders(<StatementUploadPage />)

    await waitFor(() => {
      expect(screen.getByText('Upload Bank Statement')).toBeInTheDocument()
    })

    expect(screen.getByText(/Supported formats/)).toBeInTheDocument()
  })

  it('shows dropzone', async () => {
    renderWithProviders(<StatementUploadPage />)

    await waitFor(() => {
      expect(screen.getByText(/Drag a statement file here/)).toBeInTheDocument()
    })
  })
})
