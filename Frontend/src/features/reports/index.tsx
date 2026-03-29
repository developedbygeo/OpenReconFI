import { useState } from 'react'
import {
  Title,
  Stack,
  Select,
  Button,
  Group,
  SimpleGrid,
} from '@mantine/core'
import { IconDownload } from '@tabler/icons-react'
import { notifications } from '@mantine/notifications'
import { usePreviewReportMutation } from '../../store/api.ts'
import type { TimeframeType, ReportFormat } from '../../api/types/index.ts'
import { TimeframeSelector } from './_components/TimeframeSelector.tsx'
import { ReportPreview } from './_components/ReportPreview.tsx'

const FORMAT_OPTIONS = [
  { value: 'pdf', label: 'PDF' },
  { value: 'excel', label: 'Excel' },
]

function toYYYYMM(isoOrDate: string): string {
  const d = new Date(isoOrDate)
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  return `${y}-${m}`
}

export function ReportsPage() {
  const [timeframe, setTimeframe] = useState<string>('single_month')
  const [format, setFormat] = useState<string>('pdf')
  const [singleMonth, setSingleMonth] = useState<string | null>(null)
  const [quarter, setQuarter] = useState<string | null>(null)
  const [year, setYear] = useState<string | number>(new Date().getFullYear())
  const [fromMonth, setFromMonth] = useState<string | null>(null)
  const [toMonth, setToMonth] = useState<string | null>(null)
  const [downloading, setDownloading] = useState(false)

  const [previewReport, { data: preview }] = usePreviewReportMutation()

  const buildRequest = () => {
    const base = {
      timeframe: timeframe as TimeframeType,
      format: format as ReportFormat,
    }

    switch (timeframe) {
      case 'single_month':
        return { ...base, period: singleMonth ? toYYYYMM(singleMonth) : undefined }
      case 'quarter':
        return { ...base, quarter: quarter ? Number(quarter) : undefined, year: Number(year) }
      case 'ytd':
      case 'full_year':
        return { ...base, year: Number(year) }
      case 'custom':
        return {
          ...base,
          from_period: fromMonth ? toYYYYMM(fromMonth) : undefined,
          to_period: toMonth ? toYYYYMM(toMonth) : undefined,
        }
      default:
        return base
    }
  }

  const handlePreview = async () => {
    try {
      await previewReport(buildRequest()).unwrap()
    } catch {
      notifications.show({ title: 'Error', message: 'Could not preview report.', color: 'red' })
    }
  }

  const handleDownload = async () => {
    setDownloading(true)
    try {
      const response = await fetch('/api/reports/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(buildRequest()),
      })
      if (!response.ok) throw new Error('Download failed')

      const blob = await response.blob()
      const filename = preview?.filename ?? `report.${format === 'pdf' ? 'pdf' : 'xlsx'}`
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = filename
      a.click()
      URL.revokeObjectURL(url)
    } catch {
      notifications.show({ title: 'Error', message: 'Could not download report.', color: 'red' })
    } finally {
      setDownloading(false)
    }
  }

  return (
    <Stack>
      <Title order={2}>Reports</Title>

      <SimpleGrid cols={{ base: 1, md: 2 }}>
        <TimeframeSelector
          timeframe={timeframe}
          setTimeframe={setTimeframe}
          singleMonth={singleMonth}
          setSingleMonth={setSingleMonth}
          quarter={quarter}
          setQuarter={setQuarter}
          year={year}
          setYear={setYear}
          fromMonth={fromMonth}
          setFromMonth={setFromMonth}
          toMonth={toMonth}
          setToMonth={setToMonth}
        />
        <Select
          label="Format"
          data={FORMAT_OPTIONS}
          value={format}
          onChange={(v) => setFormat(v ?? 'pdf')}
        />
      </SimpleGrid>

      <Group>
        <Button variant="light" onClick={handlePreview}>
          Preview
        </Button>
        <Button
          leftSection={<IconDownload size={16} />}
          onClick={handleDownload}
          loading={downloading}
        >
          Download
        </Button>
      </Group>

      {preview && <ReportPreview preview={preview} />}
    </Stack>
  )
}
