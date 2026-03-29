import {
  Badge,
  Group,
  Text,
  Card,
  Title,
} from '@mantine/core'
import type { MatchRead, InvoiceRead, TransactionRead } from '../../../api/types/index.ts'

export function ExceptionCard({
  exceptions,
  invoiceMap,
  txMap,
}: {
  exceptions: MatchRead[]
  invoiceMap: Map<string, InvoiceRead>
  txMap: Map<string, TransactionRead>
}) {
  return (
    <Card withBorder>
      <Title order={4} mb="xs">Flagged Exceptions</Title>
      <Text size="sm" c="dimmed" mb="sm">
        These matches scored below 70% confidence and likely need manual correction.
      </Text>
      {exceptions.map((m) => {
        const inv = invoiceMap.get(m.invoice_id)
        const tx = txMap.get(m.transaction_id)
        return (
          <Group key={m.id} justify="space-between" py="xs" style={{ borderTop: '1px solid var(--mantine-color-gray-3)' }}>
            <div>
              <Text size="sm">{inv?.vendor ?? m.invoice_id.slice(0, 8)} &harr; {tx?.counterparty ?? m.transaction_id.slice(0, 8)}</Text>
              <Text size="xs" c="dimmed">{m.rationale}</Text>
            </div>
            <Badge color="orange">{(parseFloat(m.confidence) * 100).toFixed(0)}%</Badge>
          </Group>
        )
      })}
    </Card>
  )
}
