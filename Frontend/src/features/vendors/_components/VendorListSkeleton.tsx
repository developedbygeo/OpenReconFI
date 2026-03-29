import { Stack } from '@mantine/core'
import { PageHeaderSkeleton, TableSkeleton } from '../../../components/TableSkeleton.tsx'

export function VendorListSkeleton() {
  return (
    <Stack>
      <PageHeaderSkeleton withButton />
      <TableSkeleton cols={5} rows={6} />
    </Stack>
  )
}
