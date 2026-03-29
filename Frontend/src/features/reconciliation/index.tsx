import { useState } from 'react'
import {
  Title,
  Stack,
  Button,
  Group,
  Text,
  Alert,
} from '@mantine/core'
import { useDisclosure } from '@mantine/hooks'
import { IconAlertCircle } from '@tabler/icons-react'
import { notifications } from '@mantine/notifications'
import {
  useListMatchesQuery,
  useListInvoicesQuery,
  useListTransactionsQuery,
  useTriggerMatchingMutation,
  useConfirmMatchMutation,
  useRejectMatchMutation,
  useReassignMatchMutation,
} from '../../store/api.ts'
import type { MatchRead } from '../../api/types/index.ts'
import { MatchTable } from './_components/MatchTable.tsx'
import { ExceptionCard } from './_components/ExceptionCard.tsx'
import { ReassignModal } from './_components/ReassignModal.tsx'
import { MatchReviewSkeleton } from './_components/MatchReviewSkeleton.tsx'

export { StatementUploadPage } from './_components/StatementUploadPage.tsx'
export { ReconciliationOverviewPage } from './_components/ReconciliationOverviewPage.tsx'
export { ManualMatchPage } from './_components/ManualMatchPage.tsx'

export function MatchReviewPage() {
  const { data: matchData, isLoading, error } = useListMatchesQuery({ limit: 100 })
  const { data: invoiceData } = useListInvoicesQuery({ limit: 100 })
  const { data: txData } = useListTransactionsQuery({ limit: 100 })

  const [triggerMatching, { isLoading: triggering }] = useTriggerMatchingMutation()
  const [confirmMatch] = useConfirmMatchMutation()
  const [rejectMatch] = useRejectMatchMutation()
  const [reassignMatch] = useReassignMatchMutation()

  const [opened, { open, close }] = useDisclosure(false)
  const [reassignTarget, setReassignTarget] = useState<MatchRead | null>(null)
  const [newInvoiceId, setNewInvoiceId] = useState<string | null>(null)
  const [newTransactionId, setNewTransactionId] = useState<string | null>(null)

  const invoiceMap = new Map(
    (invoiceData?.items ?? []).map((inv) => [inv.id, inv]),
  )
  const txMap = new Map(
    (txData?.items ?? []).map((tx) => [tx.id, tx]),
  )

  const handleTrigger = async () => {
    try {
      const res = await triggerMatching({}).unwrap()
      notifications.show({
        title: 'Matching complete',
        message: `${res.deterministic_matches} deterministic + ${res.llm_matches} LLM matches`,
        color: 'green',
      })
    } catch {
      notifications.show({ title: 'Matching failed', message: 'Could not run matching.', color: 'red' })
    }
  }

  const handleConfirm = async (matchId: string) => {
    try {
      await confirmMatch(matchId).unwrap()
      notifications.show({ title: 'Confirmed', message: 'Match confirmed.', color: 'green' })
    } catch {
      notifications.show({ title: 'Error', message: 'Could not confirm match.', color: 'red' })
    }
  }

  const handleReject = async (matchId: string) => {
    try {
      await rejectMatch(matchId).unwrap()
      notifications.show({ title: 'Rejected', message: 'Match rejected.', color: 'orange' })
    } catch {
      notifications.show({ title: 'Error', message: 'Could not reject match.', color: 'red' })
    }
  }

  const openReassign = (match: MatchRead) => {
    setReassignTarget(match)
    setNewInvoiceId(match.invoice_id)
    setNewTransactionId(match.transaction_id)
    open()
  }

  const handleReassign = async () => {
    if (!reassignTarget) return
    try {
      await reassignMatch({
        matchId: reassignTarget.id,
        body: {
          invoice_id: newInvoiceId,
          transaction_id: newTransactionId,
        },
      }).unwrap()
      notifications.show({ title: 'Reassigned', message: 'Match reassigned.', color: 'blue' })
      close()
    } catch {
      notifications.show({ title: 'Error', message: 'Could not reassign match.', color: 'red' })
    }
  }

  const matches = matchData?.items ?? []

  const exceptions = matches.filter(
    (m) => parseFloat(m.confidence) < 0.7 && m.confirmed_by !== 'user',
  )

  return (
    <Stack>
      <Group justify="space-between">
        <Title order={2}>Match Review</Title>
        <Button onClick={handleTrigger} loading={triggering}>
          Run Matching
        </Button>
      </Group>

      {isLoading && <MatchReviewSkeleton />}

      {error && (
        <Alert icon={<IconAlertCircle size={16} />} color="red" title="Error">
          Failed to load matches.
        </Alert>
      )}

      {exceptions.length > 0 && (
        <Alert color="orange" title={`${exceptions.length} exception(s) flagged`}>
          <Text size="sm">
            The following matches have low confidence (&lt;70%) and need manual review.
          </Text>
        </Alert>
      )}

      {matches.length === 0 && !isLoading && (
        <Text c="dimmed">No matches to review. Upload a statement and run matching.</Text>
      )}

      {matches.length > 0 && (
        <MatchTable
          matches={matches}
          invoiceMap={invoiceMap}
          txMap={txMap}
          onConfirm={handleConfirm}
          onReject={handleReject}
          onReassign={openReassign}
        />
      )}

      {exceptions.length > 0 && (
        <ExceptionCard
          exceptions={exceptions}
          invoiceMap={invoiceMap}
          txMap={txMap}
        />
      )}

      <ReassignModal
        opened={opened}
        onClose={close}
        invoices={invoiceData?.items ?? []}
        transactions={txData?.items ?? []}
        newInvoiceId={newInvoiceId}
        setNewInvoiceId={setNewInvoiceId}
        newTransactionId={newTransactionId}
        setNewTransactionId={setNewTransactionId}
        onReassign={handleReassign}
      />
    </Stack>
  )
}
