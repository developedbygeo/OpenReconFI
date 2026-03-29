import { Stack, Group, Skeleton, Table } from '@mantine/core'

export function VendorDetailSkeleton() {
  return (
    <Stack>
      <Group>
        <Skeleton h={36} w={80} radius="sm" />
      </Group>

      <Group justify="space-between">
        <Skeleton h={28} w={200} />
        <Group>
          <Skeleton h={24} w={90} radius="xl" />
          <Skeleton h={36} w={80} radius="sm" />
        </Group>
      </Group>

      <Table>
        <Table.Tbody>
          {Array.from({ length: 3 }).map((_, i) => (
            <Table.Tr key={i}>
              <Table.Th><Skeleton h={12} w={130} /></Table.Th>
              <Table.Td><Skeleton h={12} w={`${40 + (i % 3) * 20}%`} /></Table.Td>
            </Table.Tr>
          ))}
        </Table.Tbody>
      </Table>

      <Skeleton h={22} w={160} />

      <Table>
        <Table.Thead>
          <Table.Tr>
            {Array.from({ length: 5 }).map((_, i) => (
              <Table.Th key={i}><Skeleton h={12} w={`${50 + (i % 3) * 15}%`} /></Table.Th>
            ))}
          </Table.Tr>
        </Table.Thead>
        <Table.Tbody>
          {Array.from({ length: 4 }).map((_, r) => (
            <Table.Tr key={r}>
              {Array.from({ length: 5 }).map((_, c) => (
                <Table.Td key={c}><Skeleton h={12} w={`${40 + ((r + c) % 4) * 15}%`} /></Table.Td>
              ))}
            </Table.Tr>
          ))}
        </Table.Tbody>
      </Table>
    </Stack>
  )
}
