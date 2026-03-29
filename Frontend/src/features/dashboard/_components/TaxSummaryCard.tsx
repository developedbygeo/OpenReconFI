import {
  Card,
  Title,
  Text,
  Table,
  Group,
  Badge,
  Stack,
} from '@mantine/core'
import { IconReceipt2 } from '@tabler/icons-react'
import type { TaxSummary } from '../../../api/types/index.ts'

function fmt(n: number | string): string {
  const v = Number(n)
  return v < 0
    ? `-€${Math.abs(v).toFixed(2)}`
    : `€${v.toFixed(2)}`
}

export function TaxSummaryCard({ tax, onCategoryClick }: { tax?: TaxSummary | null; onCategoryClick?: (category: string) => void }) {
  const hasData = tax && tax.transaction_count > 0

  return (
    <Card withBorder>
      <Group mb="sm">
        <IconReceipt2 size={20} />
        <Title order={4}>Tax &amp; Non-Invoice Costs</Title>
      </Group>

      {!hasData ? (
        <Text c="dimmed" size="sm">No tax or non-invoice cost data available.</Text>
      ) : (
        <>
          <Group gap="sm" mb="md">
            <Badge color="red" variant="light" size="lg">
              {fmt(tax.total_amount)}
            </Badge>
            <Badge color="gray" variant="light">
              {tax.transaction_count} transaction{tax.transaction_count !== 1 ? 's' : ''}
            </Badge>
          </Group>

          {tax.by_category.length > 0 && (
            <Stack gap="xs">
              <Text size="xs" c="dimmed" tt="uppercase" fw={600}>Breakdown</Text>
              <Table striped highlightOnHover>
                <Table.Thead>
                  <Table.Tr>
                    <Table.Th>Category</Table.Th>
                    <Table.Th ta="right">Amount</Table.Th>
                    <Table.Th ta="right">Transactions</Table.Th>
                  </Table.Tr>
                </Table.Thead>
                <Table.Tbody>
                  {tax.by_category
                    .slice()
                    .sort((a, b) => Number(a.total_amount) - Number(b.total_amount))
                    .map((row) => (
                      <Table.Tr
                        key={row.category}
                        onClick={() => onCategoryClick?.(row.category)}
                        style={{ cursor: onCategoryClick ? 'pointer' : undefined }}
                      >
                        <Table.Td fw={500}>{row.category}</Table.Td>
                        <Table.Td ta="right">{fmt(row.total_amount)}</Table.Td>
                        <Table.Td ta="right">{row.transaction_count}</Table.Td>
                      </Table.Tr>
                    ))}
                </Table.Tbody>
              </Table>
            </Stack>
          )}
        </>
      )}
    </Card>
  )
}
