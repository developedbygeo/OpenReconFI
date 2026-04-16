import { useState } from 'react'
import {
  Card,
  Title,
  Text,
  Table,
  Badge,
  Group,
  Stack,
  SimpleGrid,
  Progress,
  Alert,
  Loader,
  Button,
  Modal,
  Textarea,
  Select,
  ScrollArea,
} from '@mantine/core'
import { useDisclosure } from '@mantine/hooks'
import { IconCheck, IconAlertTriangle, IconX, IconArrowBack, IconClock, IconFolderPlus } from '@tabler/icons-react'
import { notifications } from '@mantine/notifications'
import { useNavigate } from 'react-router-dom'
import { useReconciliationOverviewQuery, useDismissTransactionMutation, useUndismissTransactionMutation, useUpdateTransactionMutation } from '../../../store/reconciliationApi.ts'
import { useUpdateInvoiceMutation } from '../../../store/invoicesApi.ts'
import { useCreatePeriodSummaryMutation } from '../../../store/reportsApi.ts'
import { useListCategoriesQuery } from '../../../store/categoriesApi.ts'
import type { UnmatchedTransactionSummary } from '../../../api/types/index.ts'
import { formatMoney } from '../../../utils/format.ts'

export function ReconciliationOverview({ period }: { period: string }) {
  const navigate = useNavigate()
  const { data, isLoading, error } = useReconciliationOverviewQuery(
    { period },
    { skip: !period },
  )
  const [dismissTx] = useDismissTransactionMutation()
  const [undismissTx] = useUndismissTransactionMutation()
  const [updateTx] = useUpdateTransactionMutation()
  const [updateInvoice] = useUpdateInvoiceMutation()
  const [createSummary, { isLoading: creatingSummary }] = useCreatePeriodSummaryMutation()

  const handleCreateSummary = async () => {
    try {
      const result = await createSummary({ period }).unwrap()
      notifications.show({
        title: 'Summary folder created',
        message: `${result.invoices_copied} invoices copied to Drive.`,
        color: 'green',
      })
      window.open(result.folder_url, '_blank')
    } catch (err: unknown) {
      const msg = (err as { data?: { detail?: string } })?.data?.detail ?? 'Could not create summary folder.'
      notifications.show({ title: 'Error', message: msg, color: 'red' })
    }
  }

  const handleDeferInvoice = async (invoiceId: string) => {
    try {
      await updateInvoice({ invoiceId, body: { status: 'deferred' } }).unwrap()
      notifications.show({ title: 'Deferred', message: 'Invoice deferred to next month.', color: 'blue' })
    } catch {
      notifications.show({ title: 'Error', message: 'Could not defer invoice.', color: 'red' })
    }
  }
  const { data: categoriesData } = useListCategoriesQuery()
  const categoryNames = categoriesData?.map((c) => c.name) ?? []

  const [opened, { open, close }] = useDisclosure(false)
  const [target, setTarget] = useState<UnmatchedTransactionSummary | null>(null)
  const [note, setNote] = useState('')

  const handleTxCategoryChange = async (txId: string, category: string | null) => {
    try {
      await updateTx({ transactionId: txId, body: { category } }).unwrap()
    } catch {
      notifications.show({ title: 'Update failed', message: 'Could not update category.', color: 'red' })
    }
  }

  const handleUndismiss = async (txId: string) => {
    try {
      await undismissTx(txId).unwrap()
      notifications.show({ title: 'Restored', message: 'Transaction restored to unmatched.', color: 'green' })
    } catch {
      notifications.show({ title: 'Error', message: 'Could not restore transaction.', color: 'red' })
    }
  }

  const openDismiss = (tx: UnmatchedTransactionSummary) => {
    setTarget(tx)
    setNote('')
    open()
  }

  const handleDismiss = async () => {
    if (!target) return
    try {
      await dismissTx({ transactionId: target.id, body: { note: note.trim() || null } }).unwrap()
      notifications.show({ title: 'Dismissed', message: `Transaction dismissed.`, color: 'green' })
      close()
    } catch {
      notifications.show({ title: 'Error', message: 'Could not dismiss transaction.', color: 'red' })
    }
  }

  if (!period) return null
  if (isLoading) return <Loader />
  if (error || !data) {
    return (
      <Alert color="red" title="Error">
        Failed to load reconciliation overview.
      </Alert>
    )
  }

  const invoiceMatchRate = data.total_invoices > 0
    ? Math.round((data.matched_invoices / data.total_invoices) * 100)
    : 0
  const txMatchRate = data.total_transactions > 0
    ? Math.round((data.matched_transactions / data.total_transactions) * 100)
    : 0
  const gap = Number(data.gap)

  return (
    <Stack>
      <Group justify="space-between">
        <Title order={4}>Period Overview — {data.period}</Title>
        <Group gap="sm">
          <Button
            variant="light"
            size="xs"
            leftSection={<IconFolderPlus size={14} />}
            loading={creatingSummary}
            onClick={handleCreateSummary}
          >
            Export Invoices to Drive
          </Button>
          {data.is_complete ? (
            <Badge color="green" size="lg" leftSection={<IconCheck size={14} />}>Reconciled</Badge>
          ) : (
            <Badge color="orange" size="lg" leftSection={<IconAlertTriangle size={14} />}>Incomplete</Badge>
          )}
        </Group>
      </Group>

      <SimpleGrid cols={{ base: 1, xs: 2, sm: 3, md: 6 }}>
        <Card withBorder>
          <Text size="xs" c="dimmed" tt="uppercase">Invoices</Text>
          <Text size="lg" fw={700}>{data.matched_invoices}/{data.total_invoices}</Text>
          <Progress value={invoiceMatchRate} color="green" size="sm" mt={4} />
        </Card>
        <Card withBorder>
          <Text size="xs" c="dimmed" tt="uppercase">Invoiced Total</Text>
          <Text size="lg" fw={700}>{formatMoney(data.total_invoiced_incl)}</Text>
        </Card>
        <Card withBorder>
          <Text size="xs" c="dimmed" tt="uppercase">Bank Transactions</Text>
          <Text size="lg" fw={700}>{data.matched_transactions}/{data.total_transactions}</Text>
          <Progress value={txMatchRate} color="blue" size="sm" mt={4} />
        </Card>
        <Card withBorder>
          <Text size="xs" c="dimmed" tt="uppercase">Bank Debits</Text>
          <Text size="lg" fw={700}>{formatMoney(data.total_bank_debits)}</Text>
        </Card>
        <Card withBorder>
          <Text size="xs" c="dimmed" tt="uppercase">Earnings</Text>
          <Text size="lg" fw={700} c="green">{formatMoney(data.earnings_total)}</Text>
          <Text size="xs" c="dimmed">{data.earnings_count} tx</Text>
        </Card>
        <Card withBorder>
          <Text size="xs" c="dimmed" tt="uppercase">Gap</Text>
          <Text size="lg" fw={700} c={gap === 0 ? 'green' : 'red'}>
            {formatMoney(data.gap)}
          </Text>
        </Card>
      </SimpleGrid>

      <SimpleGrid cols={{ base: 1, sm: 3 }}>
        <Card withBorder>
          <Text size="xs" c="dimmed" tt="uppercase">No-Invoice Expenses</Text>
          <Text size="lg" fw={700}>{formatMoney(data.no_invoice_total)}</Text>
          <Text size="xs" c="dimmed">{data.no_invoice_count} transaction{data.no_invoice_count !== 1 ? 's' : ''}</Text>
        </Card>
        <Card withBorder>
          <Text size="xs" c="dimmed" tt="uppercase">Owner Withdrawals</Text>
          <Text size="lg" fw={700} c="orange">{formatMoney(data.withholding_total)}</Text>
          <Text size="xs" c="dimmed">{data.withholding_count} withdrawal{data.withholding_count !== 1 ? 's' : ''}</Text>
        </Card>
        <Card withBorder p={0} />
      </SimpleGrid>

      {data.unmatched_invoice_list.length > 0 && (
        <Card withBorder>
          <Title order={5} mb="xs">Unmatched Invoices</Title>
          <ScrollArea>
          <Table striped highlightOnHover miw={500}>
            <Table.Thead>
              <Table.Tr>
                <Table.Th>Vendor</Table.Th>
                <Table.Th>Invoice #</Table.Th>
                <Table.Th>Date</Table.Th>
                <Table.Th>Category</Table.Th>
                <Table.Th ta="right">Amount</Table.Th>
                <Table.Th />
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {data.unmatched_invoice_list.map((inv) => (
                <Table.Tr key={inv.id}>
                  <Table.Td fw={500} style={{ cursor: 'pointer' }} onClick={() => navigate(`/invoices/${inv.id}`)}>{inv.vendor}</Table.Td>
                  <Table.Td>{inv.invoice_number}</Table.Td>
                  <Table.Td>{inv.invoice_date}</Table.Td>
                  <Table.Td>{inv.category ?? '—'}</Table.Td>
                  <Table.Td ta="right">{formatMoney(inv.amount_incl, inv.currency)}</Table.Td>
                  <Table.Td>
                    <Button
                      size="compact-xs"
                      variant="light"
                      color="blue"
                      leftSection={<IconClock size={12} />}
                      onClick={() => handleDeferInvoice(inv.id)}
                    >
                      Defer
                    </Button>
                  </Table.Td>
                </Table.Tr>
              ))}
            </Table.Tbody>
          </Table>
          </ScrollArea>
        </Card>
      )}

      {data.unmatched_transaction_list.length > 0 && (
        <Card withBorder>
          <Title order={5} mb="xs">Unmatched Transactions</Title>
          <ScrollArea>
          <Table striped highlightOnHover miw={600}>
            <Table.Thead>
              <Table.Tr>
                <Table.Th>Counterparty</Table.Th>
                <Table.Th>Description</Table.Th>
                <Table.Th>Date</Table.Th>
                <Table.Th>Category</Table.Th>
                <Table.Th ta="right">Amount</Table.Th>
                <Table.Th />
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {data.unmatched_transaction_list.map((tx) => (
                <Table.Tr key={tx.id}>
                  <Table.Td fw={500}>{tx.counterparty || '—'}</Table.Td>
                  <Table.Td>{tx.description}</Table.Td>
                  <Table.Td>{tx.tx_date}</Table.Td>
                  <Table.Td>
                    <Select
                      size="xs"
                      placeholder="—"
                      clearable
                      data={categoryNames}
                      value={tx.category ?? null}
                      onChange={(v) => handleTxCategoryChange(tx.id, v)}
                      w={160}
                    />
                  </Table.Td>
                  <Table.Td ta="right">{formatMoney(tx.amount)}</Table.Td>
                  <Table.Td>
                    <Button
                      size="compact-xs"
                      variant="light"
                      color="red"
                      leftSection={<IconX size={12} />}
                      onClick={() => openDismiss(tx)}
                    >
                      Dismiss
                    </Button>
                  </Table.Td>
                </Table.Tr>
              ))}
            </Table.Tbody>
          </Table>
          </ScrollArea>
        </Card>
      )}

      {data.dismissed_transaction_list.length > 0 && (
        <Card withBorder>
          <Title order={5} mb="xs">Dismissed Transactions</Title>
          <ScrollArea>
          <Table striped highlightOnHover miw={600}>
            <Table.Thead>
              <Table.Tr>
                <Table.Th>Counterparty</Table.Th>
                <Table.Th>Description</Table.Th>
                <Table.Th>Date</Table.Th>
                <Table.Th>Category</Table.Th>
                <Table.Th>Note</Table.Th>
                <Table.Th ta="right">Amount</Table.Th>
                <Table.Th />
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {data.dismissed_transaction_list.map((tx) => (
                <Table.Tr key={tx.id}>
                  <Table.Td fw={500}>{tx.counterparty || '—'}</Table.Td>
                  <Table.Td>{tx.description}</Table.Td>
                  <Table.Td>{tx.tx_date}</Table.Td>
                  <Table.Td>{tx.category ?? '—'}</Table.Td>
                  <Table.Td><Text size="xs" c="dimmed">{tx.note ?? '—'}</Text></Table.Td>
                  <Table.Td ta="right">{formatMoney(tx.amount)}</Table.Td>
                  <Table.Td>
                    <Button
                      size="compact-xs"
                      variant="light"
                      color="blue"
                      leftSection={<IconArrowBack size={12} />}
                      onClick={() => handleUndismiss(tx.id)}
                    >
                      Undo
                    </Button>
                  </Table.Td>
                </Table.Tr>
              ))}
            </Table.Tbody>
          </Table>
          </ScrollArea>
        </Card>
      )}

      <Modal opened={opened} onClose={close} title="Dismiss Transaction">
        {target && (
          <Stack>
            <Text size="sm">
              <strong>{target.counterparty || target.description}</strong> — {formatMoney(target.amount)} on {target.tx_date}
            </Text>
            <Textarea
              label="Reason (optional)"
              placeholder="e.g. currency conversion fee, bank charge..."
              value={note}
              onChange={(e) => setNote(e.currentTarget.value)}
              minRows={2}
            />
            <Group justify="flex-end">
              <Button variant="subtle" onClick={close}>Cancel</Button>
              <Button color="red" onClick={handleDismiss}>Dismiss</Button>
            </Group>
          </Stack>
        )}
      </Modal>
    </Stack>
  )
}
