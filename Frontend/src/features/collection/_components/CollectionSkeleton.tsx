import { Stack, Skeleton } from '@mantine/core'
import { PageHeaderSkeleton, TableSkeleton } from '../../../components/TableSkeleton.tsx'

export function CollectionSkeleton() {
  return (
    <Stack>
      <PageHeaderSkeleton withButton />
      <Skeleton h={22} w={120} />
      <TableSkeleton cols={4} rows={4} />
    </Stack>
  )
}
