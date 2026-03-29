import { Stack, Group, Card, Skeleton } from '@mantine/core'
import { TableSkeleton } from '../../../components/TableSkeleton.tsx'

export function ManualMatchSkeleton() {
  return (
    <Stack>
      <Card withBorder>
        <Group justify="space-between">
          <Group gap="lg">
            <div>
              <Skeleton h={10} w={100} mb={6} />
              <Skeleton h={14} w={180} />
            </div>
            <Skeleton h={20} w={20} circle />
            <div>
              <Skeleton h={10} w={120} mb={6} />
              <Skeleton h={14} w={180} />
            </div>
          </Group>
          <Skeleton h={36} w={130} radius="sm" />
        </Group>
      </Card>

      <Group grow align="flex-start">
        <Card withBorder>
          <Skeleton h={18} w={160} mb="xs" />
          <TableSkeleton cols={4} rows={4} />
        </Card>
        <Card withBorder>
          <Skeleton h={18} w={180} mb="xs" />
          <TableSkeleton cols={4} rows={4} />
        </Card>
      </Group>
    </Stack>
  )
}
