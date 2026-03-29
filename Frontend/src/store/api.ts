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

export const api = createApi({
  baseQuery: fetchBaseQuery({ baseUrl: '/api' }),
  refetchOnFocus: true,
  refetchOnReconnect: true,
  tagTypes: Object.values(TAG),
  endpoints: () => ({}),
})
