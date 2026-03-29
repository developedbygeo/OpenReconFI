import { Table, Skeleton, Group } from '@mantine/core'

export function TableSkeleton({ cols = 4, rows = 6 }: { cols?: number; rows?: number }) {
  return (
    <Table striped>
      <Table.Thead>
        <Table.Tr>
          {Array.from({ length: cols }).map((_, i) => (
            <Table.Th key={i}>
              <Skeleton h={12} w={`${50 + (i % 3) * 15}%`} />
            </Table.Th>
          ))}
        </Table.Tr>
      </Table.Thead>
      <Table.Tbody>
        {Array.from({ length: rows }).map((_, r) => (
          <Table.Tr key={r}>
            {Array.from({ length: cols }).map((_, c) => (
              <Table.Td key={c}>
                <Skeleton h={12} w={`${40 + ((r + c) % 4) * 15}%`} />
              </Table.Td>
            ))}
          </Table.Tr>
        ))}
      </Table.Tbody>
    </Table>
  )
}

export function PageHeaderSkeleton({ withButton = false }: { withButton?: boolean }) {
  return (
    <Group justify="space-between" mb="md">
      <Skeleton h={28} w={200} />
      {withButton && <Skeleton h={36} w={130} radius="sm" />}
    </Group>
  )
}
