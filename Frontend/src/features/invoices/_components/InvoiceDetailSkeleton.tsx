import { Stack, Group, Skeleton, Table } from '@mantine/core'

export function InvoiceDetailSkeleton() {
  return (
    <Stack>
      <Group>
        <Skeleton h={36} w={80} radius="sm" />
      </Group>

      <Group justify="space-between">
        <Skeleton h={28} w={220} />
        <Skeleton h={24} w={80} radius="xl" />
      </Group>

      <Table>
        <Table.Tbody>
          {Array.from({ length: 9 }).map((_, i) => (
            <Table.Tr key={i}>
              <Table.Th><Skeleton h={12} w={120} /></Table.Th>
              <Table.Td><Skeleton h={12} w={`${40 + (i % 3) * 20}%`} /></Table.Td>
            </Table.Tr>
          ))}
        </Table.Tbody>
      </Table>
    </Stack>
  )
}
