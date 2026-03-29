import {
  Select,
  Group,
  NumberInput,
} from '@mantine/core'
import { MonthPickerInput } from '@mantine/dates'
import '@mantine/dates/styles.css'

const TIMEFRAME_OPTIONS = [
  { value: 'single_month', label: 'Single Month' },
  { value: 'quarter', label: 'Quarter' },
  { value: 'ytd', label: 'Year to Date' },
  { value: 'full_year', label: 'Full Year' },
  { value: 'custom', label: 'Custom Range' },
]

const QUARTER_OPTIONS = [
  { value: '1', label: 'Q1 (Jan–Mar)' },
  { value: '2', label: 'Q2 (Apr–Jun)' },
  { value: '3', label: 'Q3 (Jul–Sep)' },
  { value: '4', label: 'Q4 (Oct–Dec)' },
]

export function TimeframeSelector({
  timeframe,
  setTimeframe,
  singleMonth,
  setSingleMonth,
  quarter,
  setQuarter,
  year,
  setYear,
  fromMonth,
  setFromMonth,
  toMonth,
  setToMonth,
}: {
  timeframe: string
  setTimeframe: (v: string) => void
  singleMonth: string | null
  setSingleMonth: (v: string | null) => void
  quarter: string | null
  setQuarter: (v: string | null) => void
  year: string | number
  setYear: (v: string | number) => void
  fromMonth: string | null
  setFromMonth: (v: string | null) => void
  toMonth: string | null
  setToMonth: (v: string | null) => void
}) {
  return (
    <>
      <Select
        label="Timeframe"
        data={TIMEFRAME_OPTIONS}
        value={timeframe}
        onChange={(v) => setTimeframe(v ?? 'single_month')}
      />

      {timeframe === 'single_month' && (
        <MonthPickerInput
          label="Month"
          value={singleMonth}
          onChange={setSingleMonth}
          w={250}
        />
      )}

      {timeframe === 'quarter' && (
        <Group>
          <Select
            label="Quarter"
            data={QUARTER_OPTIONS}
            value={quarter}
            onChange={setQuarter}
            w={200}
          />
          <NumberInput
            label="Year"
            value={year}
            onChange={setYear}
            w={120}
          />
        </Group>
      )}

      {(timeframe === 'ytd' || timeframe === 'full_year') && (
        <NumberInput
          label="Year"
          value={year}
          onChange={setYear}
          w={120}
        />
      )}

      {timeframe === 'custom' && (
        <Group>
          <MonthPickerInput
            label="From"
            value={fromMonth}
            onChange={setFromMonth}
            w={200}
          />
          <MonthPickerInput
            label="To"
            value={toMonth}
            onChange={setToMonth}
            w={200}
          />
        </Group>
      )}
    </>
  )
}
