import { Title, Stack, Group } from '@mantine/core'
import { MonthPickerInput } from '@mantine/dates'
import '@mantine/dates/styles.css'
import { useSearchParams } from 'react-router-dom'
import { ReconciliationOverview } from './ReconciliationOverview.tsx'

function lastMonth(): Date {
  const d = new Date()
  d.setDate(1)
  d.setMonth(d.getMonth() - 1)
  return d
}

function toYYYYMM(d: Date): string {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`
}

function parseYYYYMM(s: string): Date {
  const [y, m] = s.split('-').map(Number)
  return new Date(y, m - 1, 1)
}

export function ReconciliationOverviewPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const raw = searchParams.get('period')
  const pickerValue = raw ? parseYYYYMM(raw) : lastMonth()
  const period = raw ?? toYYYYMM(lastMonth())

  const handleChange = (val: string | null) => {
    if (val) {
      setSearchParams({ period: toYYYYMM(new Date(val)) })
    }
  }

  return (
    <Stack>
      <Group justify="space-between" wrap="wrap">
        <Title order={2}>Reconciliation Overview</Title>
        <MonthPickerInput
          label="Period"
          value={pickerValue}
          onChange={handleChange}
          style={{ flex: '0 0 auto', minWidth: 160 }}
        />
      </Group>

      <ReconciliationOverview period={period} />
    </Stack>
  )
}
