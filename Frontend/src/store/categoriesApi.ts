import { api, TAG } from './api.ts'

const categoriesApi = api.injectEndpoints({
  endpoints: (build) => ({
    listCategories: build.query<{ id: string; name: string; color: string }[], void>({
      query: () => '/categories',
      providesTags: [TAG.CATEGORIES],
    }),
  }),
})

export const { useListCategoriesQuery } = categoriesApi
