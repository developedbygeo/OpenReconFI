import { useState } from 'react'
import {
  Title,
  Stack,
  Group,
  SimpleGrid,
  Card,
  Table,
  Text,
  Badge,
  Button,
  Alert,
  ScrollArea,
  Box,
} from '@mantine/core'
import { MonthPickerInput } from '@mantine/dates'
import '@mantine/dates/styles.css'
import { IconLink, IconAlertCircle, IconCheck } from '@tabler/icons-react'
import { notifications } from '@mantine/notifications'
import { useListInvoicesQuery } from '../../../store/invoicesApi.ts'
import { useListTransactionsQuery, useCreateMatchMutation } from '../../../store/reconciliationApi.ts'
import { formatMoney } from '../../../utils/format.ts'
import { ManualMatchSkeleton } from './ManualMatchSkeleton.tsx'

function lastMonth(): Date {
  const d = new Date()
  d.setDate(1)
  d.setMonth(d.getMonth() - 1)
  return d
}

function toYYYYMM(d: Date): string {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`
}

function prevMonth(period: string): string {
  const [y, m] = period.split('-').map(Number)
  const d = new Date(y, m - 2, 1)
  return toYYYYMM(d)
}

export function ManualMatchPage() {
  const [pickerValue, setPickerValue] = useState<string | null>(null)
  const period = pickerValue ? toYYYYMM(new Date(pickerValue)) : toYYYYMM(lastMonth())

  const [selectedInvoice, setSelectedInvoice] = useState<string | null>(null)
  const [selectedTransaction, setSelectedTransaction] = useState<string | null>(null)

  const prev = prevMonth(period)
  const { data: unmatchedInvData, isLoading: loadingUnmatched } = useListInvoicesQuery(
    { period, status: 'unmatched', limit: 100 },
  )
  const { data: pendingInvData, isLoading: loadingPending } = useListInvoicesQuery(
    { period, status: 'pending', limit: 100 },
  )
  // Also fetch unmatched invoices from previous month (cross-period matches)
  const { data: prevUnmatchedInvData, isLoading: loadingPrevUnmatched } = useListInvoicesQuery(
    { period: prev, status: 'unmatched', limit: 100 },
  )
  const { data: prevPendingInvData, isLoading: loadingPrevPending } = useListInvoicesQuery(
    { period: prev, status: 'pending', limit: 100 },
  )
  const invoiceData = {
    items: [
      ...(unmatchedInvData?.items ?? []),
      ...(pendingInvData?.items ?? []),
      ...(prevUnmatchedInvData?.items ?? []),
      ...(prevPendingInvData?.items ?? []),
    ],
    total: (unmatchedInvData?.total ?? 0) + (pendingInvData?.total ?? 0) +
      (prevUnmatchedInvData?.total ?? 0) + (prevPendingInvData?.total ?? 0),
  }
  const loadingInv = loadingUnmatched || loadingPending || loadingPrevUnmatched || loadingPrevPending
  const { data: unmatchedTxData, isLoading: loadingUnmatchedTx } = useListTransactionsQuery(
    { period, status: 'unmatched', limit: 100 },
  )
  const { data: matchedTxData, isLoading: loadingMatchedTx } = useListTransactionsQuery(
    { period, status: 'matched', limit: 100 },
  )
  const txData = {
    items: [...(unmatchedTxData?.items ?? []), ...(matchedTxData?.items ?? [])],
    total: (unmatchedTxData?.total ?? 0) + (matchedTxData?.total ?? 0),
  }
  const loadingTx = loadingUnmatchedTx || loadingMatchedTx
  const [createMatch, { isLoading: creating }] = useCreateMatchMutation()

  const invoices = invoiceData?.items ?? []
  const transactions = txData?.items ?? []
  const loading = loadingInv || loadingTx

  const handleMatch = async () => {
    if (!selectedInvoice || !selectedTransaction) return
    try {
      await createMatch({ invoice_id: selectedInvoice, transaction_id: selectedTransaction }).unwrap()
      notifications.show({ title: 'Matched', message: 'Invoice and transaction matched.', color: 'green' })
      setSelectedInvoice(null)
      setSelectedTransaction(null)
    } catch (err: unknown) {
      const msg = (err as { data?: { detail?: string } })?.data?.detail ?? 'Could not create match.'
      notifications.show({ title: 'Error', message: msg, color: 'red' })
    }
  }

  const selectedInv = invoices.find((i) => i.id === selectedInvoice)
  const selectedTx = transactions.find((t) => t.id === selectedTransaction)

  return (
    <Stack>
      <Group justify="space-between" wrap="wrap">
        <Title order={2}>Manual Matching</Title>
        <MonthPickerInput
          label="Period"
          value={pickerValue ? new Date(pickerValue) : lastMonth()}
          onChange={(v) => { setPickerValue(v); setSelectedInvoice(null); setSelectedTransaction(null) }}
          style={{ flex: '0 0 auto', minWidth: 160 }}
        />
      </Group>

      {loading && <ManualMatchSkeleton />}

      {/* Selection summary + match button */}
      <Card withBorder>
        <Stack gap="sm">
          <Group gap="lg" wrap="wrap">
            <div style={{ flex: '1 1 180px' }}>
              <Text size="xs" c="dimmed" tt="uppercase">Selected Invoice</Text>
              {selectedInv ? (
                <Text size="sm" fw={500}>{selectedInv.vendor} — {formatMoney(selectedInv.amount_incl, selectedInv.currency)}</Text>
              ) : (
                <Text size="sm" c="dimmed">Click an invoice below</Text>
              )}
            </div>
            <Box visibleFrom="sm"><IconLink size={20} color="var(--mantine-color-dimmed)" /></Box>
            <div style={{ flex: '1 1 180px' }}>
              <Text size="xs" c="dimmed" tt="uppercase">Selected Transaction</Text>
              {selectedTx ? (
                <Text size="sm" fw={500}>{selectedTx.counterparty || selectedTx.description} — {formatMoney(selectedTx.amount, selectedTx.original_currency ?? 'EUR')}</Text>
              ) : (
                <Text size="sm" c="dimmed">Click a transaction below</Text>
              )}
            </div>
          </Group>
          <Button
            leftSection={<IconCheck size={16} />}
            disabled={!selectedInvoice || !selectedTransaction}
            loading={creating}
            onClick={handleMatch}
            fullWidth
          >
            Create Match
          </Button>
        </Stack>
      </Card>

      <SimpleGrid cols={{ base: 1, md: 2 }}>
        {/* Unmatched Invoices */}
        <Card withBorder>
          <Title order={5} mb="xs">
            Unmatched Invoices
            <Badge ml="sm" size="sm" color="gray">{invoices.length}</Badge>
          </Title>
          {invoices.length === 0 && !loading && (
            <Text c="dimmed" size="sm">No unmatched invoices for this period.</Text>
          )}
          {invoices.length > 0 && (
            <ScrollArea>
            <Table striped highlightOnHover miw={400}>
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>Vendor</Table.Th>
                  <Table.Th>Invoice #</Table.Th>
                  <Table.Th>Date</Table.Th>
                  <Table.Th ta="right">Amount</Table.Th>
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {invoices.map((inv) => (
                  <Table.Tr
                    key={inv.id}
                    onClick={() => setSelectedInvoice(inv.id === selectedInvoice ? null : inv.id)}
                    style={{
                      cursor: 'pointer',
                      backgroundColor: inv.id === selectedInvoice ? 'var(--mantine-color-blue-light)' : undefined,
                    }}
                  >
                    <Table.Td fw={500}>{inv.vendor}</Table.Td>
                    <Table.Td>{inv.invoice_number}</Table.Td>
                    <Table.Td>{inv.invoice_date}</Table.Td>
                    <Table.Td ta="right">{formatMoney(inv.amount_incl, inv.currency)}</Table.Td>
                  </Table.Tr>
                ))}
              </Table.Tbody>
            </Table>
            </ScrollArea>
          )}
        </Card>

        {/* Unmatched Transactions */}
        <Card withBorder>
          <Title order={5} mb="xs">
            Transactions
            <Badge ml="sm" size="sm" color="gray">{transactions.length}</Badge>
          </Title>
          {transactions.length === 0 && !loading && (
            <Text c="dimmed" size="sm">No transactions for this period.</Text>
          )}
          {transactions.length > 0 && (
            <ScrollArea>
            <Table striped highlightOnHover miw={400}>
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>Counterparty</Table.Th>
                  <Table.Th>Description</Table.Th>
                  <Table.Th>Date</Table.Th>
                  <Table.Th ta="right">Amount</Table.Th>
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {transactions.map((tx) => (
                  <Table.Tr
                    key={tx.id}
                    onClick={() => setSelectedTransaction(tx.id === selectedTransaction ? null : tx.id)}
                    style={{
                      cursor: 'pointer',
                      backgroundColor: tx.id === selectedTransaction ? 'var(--mantine-color-green-light)' : undefined,
                    }}
                  >
                    <Table.Td fw={500}>
                      {tx.counterparty || '—'}
                      {tx.status === 'matched' && <Badge size="xs" color="green" ml={4}>matched</Badge>}
                    </Table.Td>
                    <Table.Td>{tx.description}</Table.Td>
                    <Table.Td>{tx.tx_date}</Table.Td>
                    <Table.Td ta="right">{formatMoney(tx.amount)}</Table.Td>
                  </Table.Tr>
                ))}
              </Table.Tbody>
            </Table>
            </ScrollArea>
          )}
        </Card>
      </SimpleGrid>

      {invoices.length === 0 && transactions.length === 0 && !loading && (
        <Alert icon={<IconAlertCircle size={16} />} color="green">
          All invoices and transactions are matched for this period.
        </Alert>
      )}
    </Stack>
  )
}
