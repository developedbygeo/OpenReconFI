import { api } from './api.ts'
import type { ReportRequest, ReportMeta } from '../api/types/index.ts'

const reportsApi = api.injectEndpoints({
  endpoints: (build) => ({
    previewReport: build.mutation<ReportMeta, ReportRequest>({
      query: (body) => ({
        url: '/reports/preview',
        method: 'POST',
        body,
      }),
    }),
  }),
})

export const { usePreviewReportMutation } = reportsApi
