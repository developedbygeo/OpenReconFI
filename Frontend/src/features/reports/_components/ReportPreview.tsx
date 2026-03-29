import {
  Title,
  Card,
  Text,
  Badge,
  Group,
} from '@mantine/core'
import type { ReportMeta } from '../../../api/types/reportMeta.ts'

export function ReportPreview({ preview }: { preview: ReportMeta }) {
  return (
    <Card withBorder>
      <Title order={4} mb="xs">Report Preview</Title>
      <Group>
        <Badge color="blue">{preview.timeframe_label}</Badge>
        <Badge color="gray">{preview.format.toUpperCase()}</Badge>
      </Group>
      <Text size="sm" mt="xs">Filename: <strong>{preview.filename}</strong></Text>
      <Text size="sm">Periods: {preview.periods.join(', ')}</Text>
    </Card>
  )
}
