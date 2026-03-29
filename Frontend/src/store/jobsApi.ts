import { api, TAG } from './api.ts'
import type {
  JobList,
  JobRead,
  JobTrigger,
  ListJobsJobsGetParams,
} from '../api/types/index.ts'

const URL = {
  JOBS: '/jobs',
  JOB: (id: string) => `/jobs/${id}`,
} as const

const jobsApi = api.injectEndpoints({
  endpoints: (build) => ({
    listJobs: build.query<JobList, ListJobsJobsGetParams | void>({
      query: (params) => ({
        url: URL.JOBS,
        params: params ?? undefined,
      }),
      providesTags: [TAG.JOBS],
    }),

    getJob: build.query<JobRead, string>({
      query: (id) => URL.JOB(id),
      providesTags: (_r, _e, id) => [{ type: TAG.JOBS, id }],
    }),

    triggerJob: build.mutation<JobRead, JobTrigger>({
      query: (body) => ({
        url: URL.JOBS,
        method: 'POST',
        body,
      }),
      invalidatesTags: [TAG.JOBS],
    }),
  }),
})

export const {
  useListJobsQuery,
  useGetJobQuery,
  useTriggerJobMutation,
} = jobsApi
