import { api, TAG } from './api.ts'
import type {
  InvoiceList,
  VendorList,
  VendorRead,
  VendorCreate,
  VendorUpdate,
  ListVendorsVendorsGetParams,
  GetVendorInvoicesVendorsVendorIdInvoicesGetParams,
} from '../api/types/index.ts'

const URL = {
  VENDORS: '/vendors',
  VENDOR: (id: string) => `/vendors/${id}`,
  VENDOR_INVOICES: (id: string) => `/vendors/${id}/invoices`,
} as const

const vendorsApi = api.injectEndpoints({
  endpoints: (build) => ({
    listVendors: build.query<VendorList, ListVendorsVendorsGetParams | void>({
      query: (params) => ({
        url: URL.VENDORS,
        params: params ?? undefined,
      }),
      providesTags: [TAG.VENDORS],
    }),

    getVendor: build.query<VendorRead, string>({
      query: (id) => URL.VENDOR(id),
      providesTags: (_r, _e, id) => [{ type: TAG.VENDORS, id }],
    }),

    createVendor: build.mutation<VendorRead, VendorCreate>({
      query: (body) => ({
        url: URL.VENDORS,
        method: 'POST',
        body,
      }),
      invalidatesTags: [TAG.VENDORS],
    }),

    updateVendor: build.mutation<VendorRead, { vendorId: string; body: VendorUpdate }>({
      query: ({ vendorId, body }) => ({
        url: URL.VENDOR(vendorId),
        method: 'PATCH',
        body,
      }),
      invalidatesTags: [TAG.VENDORS],
    }),

    deleteVendor: build.mutation<VendorRead, string>({
      query: (vendorId) => ({
        url: URL.VENDOR(vendorId),
        method: 'DELETE',
      }),
      invalidatesTags: [TAG.VENDORS],
    }),

    getVendorInvoices: build.query<InvoiceList, { vendorId: string; params?: GetVendorInvoicesVendorsVendorIdInvoicesGetParams }>({
      query: ({ vendorId, params }) => ({
        url: URL.VENDOR_INVOICES(vendorId),
        params,
      }),
      providesTags: [TAG.INVOICES],
    }),
  }),
})

export const {
  useListVendorsQuery,
  useGetVendorQuery,
  useCreateVendorMutation,
  useUpdateVendorMutation,
  useDeleteVendorMutation,
  useGetVendorInvoicesQuery,
} = vendorsApi
