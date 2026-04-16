import { api, TAG } from './api.ts'
import type {
  TransactionList,
  ListTransactionsReconciliationTransactionsGetParams,
  TransactionRead,
  TransactionDismiss,
  MatchList,
  MatchRead,
  MatchCreate,
  ListMatchesReconciliationMatchesGetParams,
  MatchTriggerRequest,
  MatchTriggerResponse,
  MatchReassign,
  StatementUploadResponse,
  PeriodReconciliation,
} from '../api/types/index.ts'

const URL = {
  UPLOAD: '/reconciliation/upload',
  TRANSACTIONS: '/reconciliation/transactions',
  TRANSACTION: (id: string) => `/reconciliation/transactions/${id}`,
  TRANSACTION_DISMISS: (id: string) => `/reconciliation/transactions/${id}/dismiss`,
  TRANSACTION_UNDISMISS: (id: string) => `/reconciliation/transactions/${id}/undismiss`,
  MATCH_TRIGGER: '/reconciliation/match',
  MATCHES: '/reconciliation/matches',
  MATCH: (id: string) => `/reconciliation/matches/${id}`,
  MATCH_CONFIRM: (id: string) => `/reconciliation/matches/${id}/confirm`,
  MATCH_REASSIGN: (id: string) => `/reconciliation/matches/${id}/reassign`,
  OVERVIEW: '/reconciliation/overview',
} as const

const reconciliationApi = api.injectEndpoints({
  endpoints: (build) => ({
    uploadStatement: build.mutation<StatementUploadResponse, FormData>({
      query: (formData) => ({
        url: URL.UPLOAD,
        method: 'POST',
        body: formData,
      }),
      invalidatesTags: [TAG.TRANSACTIONS],
    }),

    listTransactions: build.query<TransactionList, ListTransactionsReconciliationTransactionsGetParams | void>({
      query: (params) => ({
        url: URL.TRANSACTIONS,
        params: params ?? undefined,
      }),
      providesTags: [TAG.TRANSACTIONS],
    }),

    updateTransaction: build.mutation<TransactionRead, { transactionId: string; body: { category?: string | null; note?: string | null } }>({
      query: ({ transactionId, body }) => ({
        url: URL.TRANSACTION(transactionId),
        method: 'PATCH',
        body,
      }),
      invalidatesTags: [TAG.TRANSACTIONS, TAG.MATCHES],
    }),

    dismissTransaction: build.mutation<TransactionRead, { transactionId: string; body: TransactionDismiss }>({
      query: ({ transactionId, body }) => ({
        url: URL.TRANSACTION_DISMISS(transactionId),
        method: 'POST',
        body,
      }),
      invalidatesTags: [TAG.TRANSACTIONS, TAG.MATCHES],
    }),

    undismissTransaction: build.mutation<TransactionRead, string>({
      query: (transactionId) => ({
        url: URL.TRANSACTION_UNDISMISS(transactionId),
        method: 'POST',
      }),
      invalidatesTags: [TAG.TRANSACTIONS, TAG.MATCHES],
    }),

    triggerMatching: build.mutation<MatchTriggerResponse, MatchTriggerRequest>({
      query: (body) => ({
        url: URL.MATCH_TRIGGER,
        method: 'POST',
        body,
      }),
      invalidatesTags: [TAG.MATCHES],
    }),

    listMatches: build.query<MatchList, ListMatchesReconciliationMatchesGetParams | void>({
      query: (params) => ({
        url: URL.MATCHES,
        params: params ?? undefined,
      }),
      providesTags: [TAG.MATCHES],
    }),

    createMatch: build.mutation<MatchRead, MatchCreate>({
      query: (body) => ({
        url: URL.MATCHES,
        method: 'POST',
        body,
      }),
      invalidatesTags: [TAG.MATCHES, TAG.INVOICES, TAG.TRANSACTIONS],
    }),

    confirmMatch: build.mutation<MatchRead, string>({
      query: (matchId) => ({
        url: URL.MATCH_CONFIRM(matchId),
        method: 'POST',
        body: {},
      }),
      invalidatesTags: [TAG.MATCHES, TAG.INVOICES, TAG.TRANSACTIONS],
    }),

    rejectMatch: build.mutation<MatchRead, string>({
      query: (matchId) => ({
        url: URL.MATCH(matchId),
        method: 'DELETE',
      }),
      invalidatesTags: [TAG.MATCHES, TAG.INVOICES, TAG.TRANSACTIONS],
    }),

    reassignMatch: build.mutation<MatchRead, { matchId: string; body: MatchReassign }>({
      query: ({ matchId, body }) => ({
        url: URL.MATCH_REASSIGN(matchId),
        method: 'PATCH',
        body,
      }),
      invalidatesTags: [TAG.MATCHES, TAG.INVOICES, TAG.TRANSACTIONS],
    }),

    reconciliationOverview: build.query<PeriodReconciliation, { period: string }>({
      query: ({ period }) => ({
        url: URL.OVERVIEW,
        params: { period },
      }),
      providesTags: [TAG.MATCHES, TAG.INVOICES, TAG.TRANSACTIONS],
    }),
  }),
})

export const {
  useUploadStatementMutation,
  useListTransactionsQuery,
  useUpdateTransactionMutation,
  useDismissTransactionMutation,
  useUndismissTransactionMutation,
  useTriggerMatchingMutation,
  useListMatchesQuery,
  useCreateMatchMutation,
  useConfirmMatchMutation,
  useRejectMatchMutation,
  useReassignMatchMutation,
  useReconciliationOverviewQuery,
} = reconciliationApi
