import {
  Table,
  Badge,
  Button,
  Group,
  Text,
  Progress,
  ScrollArea,
} from '@mantine/core'
import { IconCheck, IconX, IconArrowsShuffle } from '@tabler/icons-react'
import type { MatchRead, InvoiceRead, TransactionRead } from '../../../api/types/index.ts'
import { formatMoney } from '../../../utils/format.ts'

function confidenceColor(c: number) {
  if (c >= 0.9) return 'green'
  if (c >= 0.7) return 'yellow'
  return 'red'
}

export function MatchTable({
  matches,
  invoiceMap,
  txMap,
  onConfirm,
  onReject,
  onReassign,
}: {
  matches: MatchRead[]
  invoiceMap: Map<string, InvoiceRead>
  txMap: Map<string, TransactionRead>
  onConfirm: (matchId: string) => void
  onReject: (matchId: string) => void
  onReassign: (match: MatchRead) => void
}) {
  return (
    <ScrollArea>
    <Table striped highlightOnHover miw={700}>
      <Table.Thead>
        <Table.Tr>
          <Table.Th>Invoice</Table.Th>
          <Table.Th>Transaction</Table.Th>
          <Table.Th>Confidence</Table.Th>
          <Table.Th>Rationale</Table.Th>
          <Table.Th>Status</Table.Th>
          <Table.Th>Actions</Table.Th>
        </Table.Tr>
      </Table.Thead>
      <Table.Tbody>
        {matches.map((match) => {
          const inv = invoiceMap.get(match.invoice_id)
          const tx = txMap.get(match.transaction_id)
          const conf = parseFloat(match.confidence)
          const isException = conf < 0.7 && match.confirmed_by !== 'user'

          return (
            <Table.Tr
              key={match.id}
              style={isException ? { backgroundColor: 'var(--mantine-color-orange-light)' } : undefined}
            >
              <Table.Td>
                <Text size="sm" fw={500}>{inv?.vendor ?? match.invoice_id.slice(0, 8)}</Text>
                {inv && <Text size="xs" c="dimmed">{formatMoney(inv.amount_incl, inv.currency)} &middot; {inv.invoice_date}</Text>}
              </Table.Td>
              <Table.Td>
                <Text size="sm" fw={500}>{tx?.counterparty ?? match.transaction_id.slice(0, 8)}</Text>
                {tx && <Text size="xs" c="dimmed">{formatMoney(tx.amount)} &middot; {tx.tx_date}</Text>}
              </Table.Td>
              <Table.Td>
                <Group gap="xs">
                  <Progress
                    value={conf * 100}
                    color={confidenceColor(conf)}
                    size="sm"
                    w={60}
                  />
                  <Text size="xs">{(conf * 100).toFixed(0)}%</Text>
                </Group>
              </Table.Td>
              <Table.Td>
                <Text size="xs" lineClamp={2}>{match.rationale}</Text>
              </Table.Td>
              <Table.Td>
                {match.confirmed_by === 'user' ? (
                  <Badge color="green">Confirmed</Badge>
                ) : match.confirmed_by === 'llm' ? (
                  <Badge color="blue">LLM suggested</Badge>
                ) : (
                  <Badge color="gray">Pending</Badge>
                )}
                {isException && <Badge color="orange" mt={4}>Exception</Badge>}
              </Table.Td>
              <Table.Td>
                <Group gap="xs">
                    {match.confirmed_by !== 'user' && (
                    <Button
                      size="xs"
                      color="green"
                      variant="light"
                      leftSection={<IconCheck size={14} />}
                      onClick={() => onConfirm(match.id)}
                    >
                      Confirm
                    </Button>
                    )}
                    <Button
                      size="xs"
                      color="red"
                      variant="light"
                      leftSection={<IconX size={14} />}
                      onClick={() => onReject(match.id)}
                    >
                      Reject
                    </Button>
                    <Button
                      size="xs"
                      color="blue"
                      variant="light"
                      leftSection={<IconArrowsShuffle size={14} />}
                      onClick={() => onReassign(match)}
                    >
                      Reassign
                    </Button>
                  </Group>
              </Table.Td>
            </Table.Tr>
          )
        })}
      </Table.Tbody>
    </Table>
    </ScrollArea>
  )
}
