import { Group, Text, Badge, Alert, Stack } from '@mantine/core'
import {
  IconMail,
  IconFileInvoice,
  IconCopy,
  IconAlertTriangle,
} from '@tabler/icons-react'
import type { JobReadSummary } from '../../../api/types/index.ts'

function extractErrorMessage(raw: string): string {
  const httpMatch = raw.match(/HttpError \d+.*?returned "(.+?)"\./s)
  if (httpMatch) return httpMatch[1]

  const detailMatch = raw.match(/'message':\s*'(.+?)'/s)
  if (detailMatch) return detailMatch[1]

  return raw
}

export function JobSummary({ summary, status }: { summary?: JobReadSummary; status: string }) {
  if (!summary) return <Text c="dimmed">—</Text>

  const s = summary as Record<string, unknown>

  if (s.error) {
    const msg = extractErrorMessage(String(s.error))
    return (
      <Alert color="red" variant="light" p="xs" icon={<IconAlertTriangle size={14} />}>
        <Text size="xs" fw={500}>{msg}</Text>
      </Alert>
    )
  }

  if (s.errors && Array.isArray(s.errors) && s.errors.length > 0) {
    return (
      <Stack gap={4}>
        <SuccessStats summary={s} />
        <Alert color="orange" variant="light" p="xs" icon={<IconAlertTriangle size={14} />}>
          <Text size="xs" fw={500}>{s.errors.length} error(s)</Text>
          {s.errors.map((err: unknown, i: number) => (
            <Text key={i} size="xs" c="dimmed">{extractErrorMessage(String(err))}</Text>
          ))}
        </Alert>
      </Stack>
    )
  }

  if (status === 'done') {
    return <SuccessStats summary={s} />
  }

  return <Text size="xs" c="dimmed">Processing...</Text>
}

function SuccessStats({ summary }: { summary: Record<string, unknown> }) {
  const emails = summary.emails_found as number | undefined
  const invoices = summary.invoices_processed as number | undefined
  const skipped = summary.skipped_duplicates as number | undefined

  return (
    <Group gap="sm" wrap="wrap">
      {emails != null && (
        <Badge variant="light" color="blue" leftSection={<IconMail size={12} />}>
          {emails} email{emails !== 1 ? 's' : ''} found
        </Badge>
      )}
      {invoices != null && (
        <Badge variant="light" color="green" leftSection={<IconFileInvoice size={12} />}>
          {invoices} invoice{invoices !== 1 ? 's' : ''} processed
        </Badge>
      )}
      {skipped != null && skipped > 0 && (
        <Badge variant="light" color="gray" leftSection={<IconCopy size={12} />}>
          {skipped} duplicate{skipped !== 1 ? 's' : ''} skipped
        </Badge>
      )}
    </Group>
  )
}
