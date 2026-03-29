import { Stack } from '@mantine/core'
import { PageHeaderSkeleton, TableSkeleton } from '../../../components/TableSkeleton.tsx'

export function InvoiceListSkeleton() {
  return (
    <Stack>
      <PageHeaderSkeleton />
      <TableSkeleton cols={6} rows={8} />
    </Stack>
  )
}
