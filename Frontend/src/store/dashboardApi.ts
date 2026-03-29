import { api, TAG } from './api.ts'
import type {
  MissingInvoiceAlertList,
  MissingInvoiceAlertsDashboardMissingInvoicesGetParams,
  SpendSummary,
  SpendSummaryDashboardSpendSummaryGetParams,
  CategorySpendList,
  SpendByCategoryDashboardSpendByCategoryGetParams,
  VendorSpendList,
  SpendByVendorDashboardSpendByVendorGetParams,
  VATSummary,
  VatSummaryDashboardVatSummaryGetParams,
  MoMComparison,
  MomComparisonDashboardMomComparisonGetParams,
} from '../api/types/index.ts'

const URL = {
  MISSING_INVOICES: '/dashboard/missing-invoices',
  SPEND_SUMMARY: '/dashboard/spend-summary',
  SPEND_BY_CATEGORY: '/dashboard/spend-by-category',
  SPEND_BY_VENDOR: '/dashboard/spend-by-vendor',
  VAT_SUMMARY: '/dashboard/vat-summary',
  MOM_COMPARISON: '/dashboard/mom-comparison',
} as const

const dashboardApi = api.injectEndpoints({
  endpoints: (build) => ({
    missingInvoiceAlerts: build.query<MissingInvoiceAlertList, MissingInvoiceAlertsDashboardMissingInvoicesGetParams | void>({
      query: (params) => ({
        url: URL.MISSING_INVOICES,
        params: params ?? undefined,
      }),
      providesTags: [TAG.MISSING_INVOICES],
    }),

    spendSummary: build.query<SpendSummary, SpendSummaryDashboardSpendSummaryGetParams | void>({
      query: (params) => ({
        url: URL.SPEND_SUMMARY,
        params: params ?? undefined,
      }),
    }),

    spendByCategory: build.query<CategorySpendList, SpendByCategoryDashboardSpendByCategoryGetParams | void>({
      query: (params) => ({
        url: URL.SPEND_BY_CATEGORY,
        params: params ?? undefined,
      }),
    }),

    spendByVendor: build.query<VendorSpendList, SpendByVendorDashboardSpendByVendorGetParams | void>({
      query: (params) => ({
        url: URL.SPEND_BY_VENDOR,
        params: params ?? undefined,
      }),
    }),

    vatSummary: build.query<VATSummary, VatSummaryDashboardVatSummaryGetParams | void>({
      query: (params) => ({
        url: URL.VAT_SUMMARY,
        params: params ?? undefined,
      }),
    }),

    momComparison: build.query<MoMComparison, MomComparisonDashboardMomComparisonGetParams | void>({
      query: (params) => ({
        url: URL.MOM_COMPARISON,
        params: params ?? undefined,
      }),
    }),
  }),
})

export const {
  useMissingInvoiceAlertsQuery,
  useSpendSummaryQuery,
  useSpendByCategoryQuery,
  useSpendByVendorQuery,
  useVatSummaryQuery,
  useMomComparisonQuery,
} = dashboardApi
