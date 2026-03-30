import { createApi, fetchBaseQuery } from '@reduxjs/toolkit/query/react'

export const TAG = {
  CATEGORIES: 'Categories',
  INVOICES: 'Invoices',
  JOBS: 'Jobs',
  TRANSACTIONS: 'Transactions',
  MATCHES: 'Matches',
  VENDORS: 'Vendors',
  MISSING_INVOICES: 'MissingInvoices',
  CHAT: 'Chat',
} as const

const isTest = import.meta.env?.MODE === 'test'

export const api = createApi({
  baseQuery: fetchBaseQuery({ baseUrl: isTest ? 'http://localhost:3000/api' : '/api' }),
  refetchOnFocus: true,
  refetchOnReconnect: true,
  tagTypes: Object.values(TAG),
  endpoints: () => ({}),
})
