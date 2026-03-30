import { type ReactElement } from 'react'
import { render, type RenderOptions } from '@testing-library/react'
import { Provider } from 'react-redux'
import { MantineProvider } from '@mantine/core'
import { MemoryRouter } from 'react-router-dom'
import { configureStore } from '@reduxjs/toolkit'
import { api } from '../store/api.ts'

interface Options extends Omit<RenderOptions, 'wrapper'> {
  route?: string
}

function createTestStore() {
  return configureStore({
    reducer: { [api.reducerPath]: api.reducer },
    middleware: (getDefault) => getDefault().concat(api.middleware),
  })
}

export function renderWithProviders(ui: ReactElement, { route = '/', ...options }: Options = {}) {
  const store = createTestStore()

  function Wrapper({ children }: { children: React.ReactNode }) {
    return (
      <Provider store={store}>
        <MantineProvider>
          <MemoryRouter initialEntries={[route]}>
            {children}
          </MemoryRouter>
        </MantineProvider>
      </Provider>
    )
  }

  return { ...render(ui, { wrapper: Wrapper, ...options }), store }
}
