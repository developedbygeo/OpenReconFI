import { Stack } from '@mantine/core'
import { PageHeaderSkeleton, TableSkeleton } from '../../../components/TableSkeleton.tsx'

export function MatchReviewSkeleton() {
  return (
    <Stack>
      <PageHeaderSkeleton withButton />
      <TableSkeleton cols={6} rows={6} />
    </Stack>
  )
}
