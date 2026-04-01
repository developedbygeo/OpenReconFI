import { useState } from 'react'
import {
  Table,
  Badge,
  Title,
  Stack,
  Group,
  Select,
  Anchor,
  Alert,
  Text,
  Pagination,
  ScrollArea,
} from '@mantine/core'
import { notifications } from '@mantine/notifications'
import { IconExternalLink, IconAlertCircle } from '@tabler/icons-react'
import { useNavigate } from 'react-router-dom'
import { useListInvoicesQuery, useUpdateInvoiceMutation } from '../../../store/invoicesApi.ts'
import { useListCategoriesQuery } from '../../../store/categoriesApi.ts'
import type { InvoiceStatus } from '../../../api/types/index.ts'
import { formatMoney } from '../../../utils/format.ts'
import { InvoiceListSkeleton } from './InvoiceListSkeleton.tsx'

const STATUS_COLORS: Record<string, string> = {
  pending: 'yellow',
  matched: 'green',
  unmatched: 'orange',
  flagged: 'red',
}

const PAGE_SIZE = 20

export function InvoiceListPage() {
  const navigate = useNavigate()
  const [page, setPage] = useState(1)
  const [statusFilter, setStatusFilter] = useState<string | null>(null)
  const [categoryFilter, setCategoryFilter] = useState<string | null>(null)
  const [updateInvoice] = useUpdateInvoiceMutation()
  const { data: categoriesData } = useListCategoriesQuery()
  const categoryNames = categoriesData?.map((c) => c.name) ?? []

  const { data, isLoading, error } = useListInvoicesQuery({
    skip: (page - 1) * PAGE_SIZE,
    limit: PAGE_SIZE,
    ...(statusFilter ? { status: statusFilter } : {}),
    ...(categoryFilter ? { category: categoryFilter } : {}),
  })

  const handleCategoryChange = async (invoiceId: string, category: string | null) => {
    try {
      await updateInvoice({ invoiceId, body: { category } }).unwrap()
      notifications.show({
        title: 'Category updated',
        message: category ? `Set to ${category}` : 'Category cleared',
        color: 'green',
      })
    } catch {
      notifications.show({
        title: 'Update failed',
        message: 'Could not update category.',
        color: 'red',
      })
    }
  }

  if (isLoading) return <InvoiceListSkeleton />

  if (error) {
    return (
      <Alert icon={<IconAlertCircle size={16} />} color="red" title="Error">
        Failed to load invoices.
      </Alert>
    )
  }

  const invoices = data?.items ?? []
  const total = data?.total ?? 0

  return (
    <>
      <Stack gap="xs" mb="md">
        <Title order={2}>Invoices</Title>
        <Group wrap="wrap">
          <Select
            placeholder="Filter by category"
            clearable
            data={categoryNames}
            value={categoryFilter}
            onChange={(v) => {
              setCategoryFilter(v)
              setPage(1)
            }}
            style={{ flex: '1 1 160px', maxWidth: 200 }}
          />
          <Select
            placeholder="Filter by status"
            clearable
            data={['pending', 'matched', 'unmatched', 'flagged']}
            value={statusFilter}
            onChange={(v) => {
              setStatusFilter(v)
              setPage(1)
            }}
            style={{ flex: '1 1 140px', maxWidth: 180 }}
          />
        </Group>
      </Stack>

      {invoices.length === 0 ? (
        <Text c="dimmed">No invoices found.</Text>
      ) : (
        <>
          <ScrollArea>
          <Table striped highlightOnHover miw={600}>
            <Table.Thead>
              <Table.Tr>
                <Table.Th>Vendor</Table.Th>
                <Table.Th>Amount (incl.)</Table.Th>
                <Table.Th>Date</Table.Th>
                <Table.Th>Category</Table.Th>
                <Table.Th>Status</Table.Th>
                <Table.Th>Drive</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {invoices.map((inv) => (
                <Table.Tr
                  key={inv.id}
                  style={{ cursor: 'pointer' }}
                  onClick={() => navigate(`/invoices/${inv.id}`)}
                >
                  <Table.Td>{inv.vendor}</Table.Td>
                  <Table.Td>{formatMoney(inv.amount_incl, inv.currency)}</Table.Td>
                  <Table.Td>{inv.invoice_date}</Table.Td>
                  <Table.Td onClick={(e) => e.stopPropagation()}>
                    <Select
                      size="xs"
                      placeholder="—"
                      clearable
                      data={categoryNames}
                      value={inv.category ?? null}
                      onChange={(v) => handleCategoryChange(inv.id, v)}
                      miw={120}
                    />
                  </Table.Td>
                  <Table.Td>
                    <Badge color={STATUS_COLORS[inv.status as InvoiceStatus] ?? 'gray'}>
                      {inv.status}
                    </Badge>
                  </Table.Td>
                  <Table.Td onClick={(e) => e.stopPropagation()}>
                    {inv.drive_url ? (
                      <Anchor href={inv.drive_url} target="_blank" rel="noopener">
                        <IconExternalLink size={16} />
                      </Anchor>
                    ) : (
                      <Text c="dimmed" size="sm">—</Text>
                    )}
                  </Table.Td>
                </Table.Tr>
              ))}
            </Table.Tbody>
          </Table>
          </ScrollArea>

          {total > PAGE_SIZE && (
            <Group justify="center" mt="md">
              <Pagination
                total={Math.ceil(total / PAGE_SIZE)}
                value={page}
                onChange={setPage}
              />
            </Group>
          )}
        </>
      )}
    </>
  )
}
