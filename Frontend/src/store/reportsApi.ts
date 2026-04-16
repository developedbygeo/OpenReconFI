import { api } from './api.ts'
import type { ReportRequest, ReportMeta } from '../api/types/index.ts'

interface PeriodSummaryResponse {
  folder_url: string
  invoices_copied: number
}

const reportsApi = api.injectEndpoints({
  endpoints: (build) => ({
    previewReport: build.mutation<ReportMeta, ReportRequest>({
      query: (body) => ({
        url: '/reports/preview',
        method: 'POST',
        body,
      }),
    }),
    createPeriodSummary: build.mutation<PeriodSummaryResponse, { period: string }>({
      query: (body) => ({
        url: '/reports/period-summary',
        method: 'POST',
        body,
      }),
    }),
  }),
})

export const { usePreviewReportMutation, useCreatePeriodSummaryMutation } = reportsApi
