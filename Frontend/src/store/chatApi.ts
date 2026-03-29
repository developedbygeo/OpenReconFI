import { api, TAG } from './api.ts'
import type { ChatHistory, ChatClearResponse, ChatSuggestions } from '../api/types/index.ts'

const chatApi = api.injectEndpoints({
  endpoints: (build) => ({
    chatHistory: build.query<ChatHistory, void>({
      query: () => '/chat/history',
      providesTags: [TAG.CHAT],
    }),

    clearChatHistory: build.mutation<ChatClearResponse, void>({
      query: () => ({
        url: '/chat/history',
        method: 'DELETE',
      }),
      invalidatesTags: [TAG.CHAT],
    }),

    chatSuggestions: build.query<ChatSuggestions, void>({
      query: () => '/chat/suggestions',
      providesTags: [TAG.CHAT],
    }),
  }),
})

export const {
  useChatHistoryQuery,
  useClearChatHistoryMutation,
  useChatSuggestionsQuery,
} = chatApi
