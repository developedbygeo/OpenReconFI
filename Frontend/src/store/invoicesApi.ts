import { api, TAG } from './api.ts'
import type {
  InvoiceList,
  InvoiceRead,
  InvoiceUpdate,
  ListInvoicesInvoicesGetParams,
} from '../api/types/index.ts'

const URL = {
  INVOICES: '/invoices',
  INVOICE: (id: string) => `/invoices/${id}`,
} as const

const invoicesApi = api.injectEndpoints({
  endpoints: (build) => ({
    listInvoices: build.query<InvoiceList, ListInvoicesInvoicesGetParams | void>({
      query: (params) => ({
        url: URL.INVOICES,
        params: params ?? undefined,
      }),
      providesTags: [TAG.INVOICES],
    }),

    getInvoice: build.query<InvoiceRead, string>({
      query: (id) => URL.INVOICE(id),
      providesTags: (_r, _e, id) => [{ type: TAG.INVOICES, id }],
    }),

    updateInvoice: build.mutation<InvoiceRead, { invoiceId: string; body: InvoiceUpdate }>({
      query: ({ invoiceId, body }) => ({
        url: URL.INVOICE(invoiceId),
        method: 'PATCH',
        body,
      }),
      invalidatesTags: [TAG.INVOICES],
    }),
  }),
})

export const {
  useListInvoicesQuery,
  useGetInvoiceQuery,
  useUpdateInvoiceMutation,
} = invoicesApi
