import { useEffect, useState } from 'react'
import {
  Modal,
  Table,
  Text,
  Badge,
  Group,
  Stack,
  Loader,
  Tabs,
  Select,
  ScrollArea,
} from '@mantine/core'
import { IconBuildingStore, IconCalendar, IconReceipt } from '@tabler/icons-react'
import { notifications } from '@mantine/notifications'
import type { InvoiceRead } from '../../../api/types/index.ts'
import type { TransactionRead } from '../../../api/types/index.ts'
import { useListCategoriesQuery } from '../../../store/categoriesApi.ts'

interface VendorRow {
  vendor: string
  count: number
  totalExcl: number
  totalVat: number
  totalIncl: number
}

interface MonthRow {
  period: string
  count: number
  totalExcl: number
  totalVat: number
  totalIncl: number
}

function groupByVendor(invoices: InvoiceRead[]): VendorRow[] {
  const map = new Map<string, VendorRow>()
  for (const inv of invoices) {
    const existing = map.get(inv.vendor)
    if (existing) {
      existing.count++
      existing.totalExcl += parseFloat(inv.amount_excl)
      existing.totalVat += parseFloat(inv.vat_amount)
      existing.totalIncl += parseFloat(inv.amount_incl)
    } else {
      map.set(inv.vendor, {
        vendor: inv.vendor,
        count: 1,
        totalExcl: parseFloat(inv.amount_excl),
        totalVat: parseFloat(inv.vat_amount),
        totalIncl: parseFloat(inv.amount_incl),
      })
    }
  }
  return Array.from(map.values()).sort((a, b) => b.totalIncl - a.totalIncl)
}

function groupByMonth(invoices: InvoiceRead[]): MonthRow[] {
  const map = new Map<string, MonthRow>()
  for (const inv of invoices) {
    const existing = map.get(inv.period)
    if (existing) {
      existing.count++
      existing.totalExcl += parseFloat(inv.amount_excl)
      existing.totalVat += parseFloat(inv.vat_amount)
      existing.totalIncl += parseFloat(inv.amount_incl)
    } else {
      map.set(inv.period, {
        period: inv.period,
        count: 1,
        totalExcl: parseFloat(inv.amount_excl),
        totalVat: parseFloat(inv.vat_amount),
        totalIncl: parseFloat(inv.amount_incl),
      })
    }
  }
  return Array.from(map.values()).sort((a, b) => a.period.localeCompare(b.period))
}

function fmt(n: number | string): string {
  const v = Number(n)
  return v < 0 ? `-€${Math.abs(v).toFixed(2)}` : `€${v.toFixed(2)}`
}

async function patchCategory(txId: string, category: string): Promise<TransactionRead> {
  const res = await fetch(`/api/reconciliation/transactions/${txId}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ category }),
  })
  if (!res.ok) throw new Error('Failed to update category')
  return res.json()
}

export function CategoryDetailModal({ category, periods, opened, onClose }: {
  category: string | null
  periods: string[]
  opened: boolean
  onClose: () => void
}) {
  const { data: categoriesData } = useListCategoriesQuery()
  const categoryNames = categoriesData?.map((c) => c.name) ?? []
  const [invoices, setInvoices] = useState<InvoiceRead[]>([])
  const [transactions, setTransactions] = useState<TransactionRead[]>([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (!opened || !category) return

    setLoading(true)
    const targets = periods.length === 0 ? [''] : periods

    const invoicePromise = Promise.all(
      targets.map((p) => {
        const qs = p ? `?period=${p}&limit=100` : '?limit=100'
        return fetch(`/api/invoices${qs}`).then((r) => r.json())
      }),
    ).then((results) => {
      const all: InvoiceRead[] = results.flatMap((r: { items: InvoiceRead[] }) => r.items)
      const unique = Array.from(new Map(all.map((inv) => [inv.id, inv])).values())
      return unique.filter((inv) => inv.category === category)
    })

    const txPromise = fetch(
      `/api/reconciliation/transactions?status=no_invoice&category=${encodeURIComponent(category)}&limit=100`,
    )
      .then((r) => r.json())
      .then((r: { items: TransactionRead[] }) => r.items ?? [])

    Promise.all([invoicePromise, txPromise])
      .then(([inv, tx]) => {
        setInvoices(inv)
        setTransactions(tx)
        setLoading(false)
      })
      .catch(() => setLoading(false))
  }, [opened, category, periods.join(',')])

  const handleCategoryChange = async (txId: string, newCategory: string | null) => {
    if (!newCategory) return
    try {
      await patchCategory(txId, newCategory)
      notifications.show({ title: 'Updated', message: `Category changed to ${newCategory}`, color: 'green' })
      // Remove the transaction from the list (it's no longer in this category)
      setTransactions((prev) => prev.filter((tx) => tx.id !== txId))
    } catch {
      notifications.show({ title: 'Error', message: 'Failed to update category', color: 'red' })
    }
  }

  const byVendor = groupByVendor(invoices)
  const byMonth = groupByMonth(invoices)
  const hasInvoices = invoices.length > 0
  const hasTransactions = transactions.length > 0
  const txTotal = transactions.reduce((s, tx) => s + Number(tx.amount), 0)

  return (
    <Modal opened={opened} onClose={onClose} title={category} size="xl">
      {loading ? (
        <Group justify="center" py="xl"><Loader /></Group>
      ) : !hasInvoices && !hasTransactions ? (
        <Text c="dimmed">No data found for this category.</Text>
      ) : (
        <Stack>
          <Group gap="sm">
            {hasInvoices && (
              <Badge color="blue">{invoices.length} invoice{invoices.length !== 1 ? 's' : ''}</Badge>
            )}
            {hasInvoices && (
              <Badge color="gray">
                &euro;{invoices.reduce((s, inv) => s + parseFloat(inv.amount_incl), 0).toFixed(2)} invoiced
              </Badge>
            )}
            {hasTransactions && (
              <Badge color="orange">{transactions.length} transaction{transactions.length !== 1 ? 's' : ''}</Badge>
            )}
            {hasTransactions && (
              <Badge color="gray">{fmt(txTotal)} bank</Badge>
            )}
          </Group>

          <Tabs defaultValue={hasTransactions && !hasInvoices ? 'transactions' : 'vendor'}>
            <Tabs.List>
              {hasInvoices && (
                <>
                  <Tabs.Tab value="vendor" leftSection={<IconBuildingStore size={14} />}>
                    By Vendor
                  </Tabs.Tab>
                  <Tabs.Tab value="month" leftSection={<IconCalendar size={14} />}>
                    By Month
                  </Tabs.Tab>
                </>
              )}
              {hasTransactions && (
                <Tabs.Tab value="transactions" leftSection={<IconReceipt size={14} />}>
                  Transactions
                </Tabs.Tab>
              )}
            </Tabs.List>

            {hasInvoices && (
              <Tabs.Panel value="vendor" pt="sm">
                <ScrollArea><Table striped highlightOnHover miw={450}>
                  <Table.Thead>
                    <Table.Tr>
                      <Table.Th>Vendor</Table.Th>
                      <Table.Th ta="right">Excl. VAT</Table.Th>
                      <Table.Th ta="right">VAT</Table.Th>
                      <Table.Th ta="right">Incl. VAT</Table.Th>
                      <Table.Th ta="right">Invoices</Table.Th>
                    </Table.Tr>
                  </Table.Thead>
                  <Table.Tbody>
                    {byVendor.map((row) => (
                      <Table.Tr key={row.vendor}>
                        <Table.Td fw={500}>{row.vendor}</Table.Td>
                        <Table.Td ta="right">&euro;{row.totalExcl.toFixed(2)}</Table.Td>
                        <Table.Td ta="right">&euro;{row.totalVat.toFixed(2)}</Table.Td>
                        <Table.Td ta="right">&euro;{row.totalIncl.toFixed(2)}</Table.Td>
                        <Table.Td ta="right">{row.count}</Table.Td>
                      </Table.Tr>
                    ))}
                  </Table.Tbody>
                </Table></ScrollArea>
              </Tabs.Panel>
            )}

            {hasInvoices && (
              <Tabs.Panel value="month" pt="sm">
                <ScrollArea><Table striped highlightOnHover miw={450}>
                  <Table.Thead>
                    <Table.Tr>
                      <Table.Th>Period</Table.Th>
                      <Table.Th ta="right">Excl. VAT</Table.Th>
                      <Table.Th ta="right">VAT</Table.Th>
                      <Table.Th ta="right">Incl. VAT</Table.Th>
                      <Table.Th ta="right">Invoices</Table.Th>
                    </Table.Tr>
                  </Table.Thead>
                  <Table.Tbody>
                    {byMonth.map((row) => (
                      <Table.Tr key={row.period}>
                        <Table.Td fw={500}>{row.period}</Table.Td>
                        <Table.Td ta="right">&euro;{row.totalExcl.toFixed(2)}</Table.Td>
                        <Table.Td ta="right">&euro;{row.totalVat.toFixed(2)}</Table.Td>
                        <Table.Td ta="right">&euro;{row.totalIncl.toFixed(2)}</Table.Td>
                        <Table.Td ta="right">{row.count}</Table.Td>
                      </Table.Tr>
                    ))}
                  </Table.Tbody>
                </Table></ScrollArea>
              </Tabs.Panel>
            )}

            {hasTransactions && (
              <Tabs.Panel value="transactions" pt="sm">
                <ScrollArea><Table striped highlightOnHover miw={450}>
                  <Table.Thead>
                    <Table.Tr>
                      <Table.Th>Date</Table.Th>
                      <Table.Th>Counterparty</Table.Th>
                      <Table.Th>Description</Table.Th>
                      <Table.Th ta="right">Amount</Table.Th>
                      <Table.Th>Category</Table.Th>
                    </Table.Tr>
                  </Table.Thead>
                  <Table.Tbody>
                    {transactions.map((tx) => (
                      <Table.Tr key={tx.id}>
                        <Table.Td>{tx.tx_date}</Table.Td>
                        <Table.Td fw={500}>{tx.counterparty}</Table.Td>
                        <Table.Td>{tx.description}</Table.Td>
                        <Table.Td ta="right">{fmt(tx.amount)}</Table.Td>
                        <Table.Td>
                          <Select
                            size="xs"
                            data={categoryNames}
                            value={tx.category ?? null}
                            onChange={(val) => handleCategoryChange(tx.id, val)}
                            miw={120}
                          />
                        </Table.Td>
                      </Table.Tr>
                    ))}
                  </Table.Tbody>
                </Table></ScrollArea>
              </Tabs.Panel>
            )}
          </Tabs>
        </Stack>
      )}
    </Modal>
  )
}
