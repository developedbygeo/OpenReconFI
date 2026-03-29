import {
  Title,
  Stack,
  Group,
  Badge,
  Button,
  Alert,
  Table,
  Text,
} from '@mantine/core'
import { IconArrowLeft, IconEdit, IconAlertCircle } from '@tabler/icons-react'
import { useParams, useNavigate } from 'react-router-dom'
import { useGetVendorQuery, useGetVendorInvoicesQuery } from '../../../store/api.ts'
import { formatMoney } from '../../../utils/format.ts'
import { VendorDetailSkeleton } from './VendorDetailSkeleton.tsx'

const CYCLE_COLORS: Record<string, string> = {
  monthly: 'blue',
  bimonthly: 'cyan',
  quarterly: 'teal',
  annual: 'grape',
  irregular: 'gray',
}

const STATUS_COLORS: Record<string, string> = {
  pending: 'yellow',
  matched: 'green',
  unmatched: 'orange',
  flagged: 'red',
}

export function VendorDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const { data: vendor, isLoading, error } = useGetVendorQuery(id!)
  const { data: invoiceData } = useGetVendorInvoicesQuery({ vendorId: id!, params: { limit: 50 } })

  if (isLoading) return <VendorDetailSkeleton />

  if (error || !vendor) {
    return (
      <Alert icon={<IconAlertCircle size={16} />} color="red" title="Error">
        Failed to load vendor.
      </Alert>
    )
  }

  const invoices = invoiceData?.items ?? []

  return (
    <Stack>
      <Group>
        <Button
          variant="subtle"
          leftSection={<IconArrowLeft size={16} />}
          onClick={() => navigate('/vendors')}
        >
          Back
        </Button>
      </Group>

      <Group justify="space-between">
        <Title order={2}>{vendor.name}</Title>
        <Group>
          <Badge size="lg" color={CYCLE_COLORS[vendor.billing_cycle] ?? 'gray'}>
            {vendor.billing_cycle}
          </Badge>
          <Button
            variant="light"
            leftSection={<IconEdit size={16} />}
            onClick={() => navigate(`/vendors/${id}/edit`)}
          >
            Edit
          </Button>
        </Group>
      </Group>

      <Table>
        <Table.Tbody>
          <Table.Tr>
            <Table.Th>Default Category</Table.Th>
            <Table.Td>{vendor.default_category ?? '—'}</Table.Td>
          </Table.Tr>
          <Table.Tr>
            <Table.Th>Default VAT Rate</Table.Th>
            <Table.Td>{vendor.default_vat_rate ? `${vendor.default_vat_rate}%` : '—'}</Table.Td>
          </Table.Tr>
          <Table.Tr>
            <Table.Th>Aliases</Table.Th>
            <Table.Td>{vendor.aliases?.length ? vendor.aliases.join(', ') : '—'}</Table.Td>
          </Table.Tr>
        </Table.Tbody>
      </Table>

      <Title order={4}>Invoice History</Title>

      {invoices.length === 0 ? (
        <Text c="dimmed">No invoices for this vendor.</Text>
      ) : (
        <Table striped highlightOnHover>
          <Table.Thead>
            <Table.Tr>
              <Table.Th>Invoice #</Table.Th>
              <Table.Th>Date</Table.Th>
              <Table.Th>Amount (incl.)</Table.Th>
              <Table.Th>Period</Table.Th>
              <Table.Th>Status</Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {invoices.map((inv) => (
              <Table.Tr
                key={inv.id}
                style={{ cursor: 'pointer' }}
                onClick={() => navigate(`/invoices/${inv.id}`)}
              >
                <Table.Td>{inv.invoice_number}</Table.Td>
                <Table.Td>{inv.invoice_date}</Table.Td>
                <Table.Td>{formatMoney(inv.amount_incl, inv.currency)}</Table.Td>
                <Table.Td>{inv.period}</Table.Td>
                <Table.Td>
                  <Badge color={STATUS_COLORS[inv.status] ?? 'gray'}>
                    {inv.status}
                  </Badge>
                </Table.Td>
              </Table.Tr>
            ))}
          </Table.Tbody>
        </Table>
      )}
    </Stack>
  )
}
