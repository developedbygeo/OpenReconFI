import { useState } from 'react'
import {
  Title,
  Group,
  Badge,
  Alert,
  Table,
  Anchor,
  Button,
  Code,
  Collapse,
  Stack,
} from '@mantine/core'
import { IconAlertCircle, IconArrowLeft, IconExternalLink } from '@tabler/icons-react'
import { useParams, useNavigate } from 'react-router-dom'
import { useGetInvoiceQuery } from '../../../store/invoicesApi.ts'
import { formatMoney } from '../../../utils/format.ts'
import { InvoiceDetailSkeleton } from './InvoiceDetailSkeleton.tsx'

const STATUS_COLORS: Record<string, string> = {
  pending: 'yellow',
  matched: 'green',
  unmatched: 'orange',
  flagged: 'red',
}

export function InvoiceDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [showRaw, setShowRaw] = useState(false)

  const { data: invoice, isLoading, error } = useGetInvoiceQuery(id!)

  if (isLoading) return <InvoiceDetailSkeleton />

  if (error || !invoice) {
    return (
      <Alert icon={<IconAlertCircle size={16} />} color="red" title="Error">
        Failed to load invoice.
      </Alert>
    )
  }

  return (
    <Stack>
      <Group>
        <Button
          variant="subtle"
          leftSection={<IconArrowLeft size={16} />}
          onClick={() => navigate('/invoices')}
        >
          Back
        </Button>
      </Group>

      <Group justify="space-between">
        <Title order={2}>{invoice.vendor}</Title>
        <Badge size="lg" color={STATUS_COLORS[invoice.status] ?? 'gray'}>
          {invoice.status}
        </Badge>
      </Group>

      <Table>
        <Table.Tbody>
          <Table.Tr>
            <Table.Th>Invoice #</Table.Th>
            <Table.Td>{invoice.invoice_number}</Table.Td>
          </Table.Tr>
          <Table.Tr>
            <Table.Th>Date</Table.Th>
            <Table.Td>{invoice.invoice_date}</Table.Td>
          </Table.Tr>
          <Table.Tr>
            <Table.Th>Period</Table.Th>
            <Table.Td>{invoice.period}</Table.Td>
          </Table.Tr>
          <Table.Tr>
            <Table.Th>Amount (excl. VAT)</Table.Th>
            <Table.Td>{formatMoney(invoice.amount_excl, invoice.currency)}</Table.Td>
          </Table.Tr>
          <Table.Tr>
            <Table.Th>VAT ({invoice.vat_rate}%)</Table.Th>
            <Table.Td>{formatMoney(invoice.vat_amount, invoice.currency)}</Table.Td>
          </Table.Tr>
          <Table.Tr>
            <Table.Th>Amount (incl. VAT)</Table.Th>
            <Table.Td>{formatMoney(invoice.amount_incl, invoice.currency)}</Table.Td>
          </Table.Tr>
          <Table.Tr>
            <Table.Th>Category</Table.Th>
            <Table.Td>{invoice.category ?? '—'}</Table.Td>
          </Table.Tr>
          <Table.Tr>
            <Table.Th>Source</Table.Th>
            <Table.Td>{invoice.source}</Table.Td>
          </Table.Tr>
          <Table.Tr>
            <Table.Th>Drive</Table.Th>
            <Table.Td>
              {invoice.drive_url ? (
                <Anchor href={invoice.drive_url} target="_blank" rel="noopener">
                  Open in Drive <IconExternalLink size={14} />
                </Anchor>
              ) : (
                '—'
              )}
            </Table.Td>
          </Table.Tr>
          <Table.Tr>
            <Table.Th>Created</Table.Th>
            <Table.Td>{new Date(invoice.created_at).toLocaleString()}</Table.Td>
          </Table.Tr>
        </Table.Tbody>
      </Table>

      {invoice.raw_extraction && (
        <>
          <Button
            variant="light"
            onClick={() => setShowRaw((v) => !v)}
            w="fit-content"
          >
            {showRaw ? 'Hide' : 'Show'} raw extraction
          </Button>
          <Collapse in={showRaw}>
            <Code block>{JSON.stringify(invoice.raw_extraction, null, 2)}</Code>
          </Collapse>
        </>
      )}
    </Stack>
  )
}
