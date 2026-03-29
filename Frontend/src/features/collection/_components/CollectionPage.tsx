import { useEffect, useRef } from 'react'
import {
  Title,
  Button,
  Table,
  Badge,
  Alert,
  Stack,
  Text,
  Group,
} from '@mantine/core'
import { IconMailForward, IconAlertCircle } from '@tabler/icons-react'
import { useListJobsQuery, useTriggerJobMutation } from '../../../store/jobsApi.ts'
import { api } from '../../../store/api.ts'
import { useAppDispatch } from '../../../store/hooks.ts'
import { JobSummary } from './JobSummary.tsx'
import { CollectionSkeleton } from './CollectionSkeleton.tsx'

const STATUS_COLORS: Record<string, string> = {
  running: 'blue',
  done: 'green',
  failed: 'red',
}

const POLL_INTERVAL = 3000

export function CollectionPage() {
  const dispatch = useAppDispatch()
  const prevRunning = useRef(false)

  const { data, isLoading, error } = useListJobsQuery({ job_type: 'gmail_sync' })
  const [triggerJob, { isLoading: triggering }] = useTriggerJobMutation()

  const anyRunning = data?.items.some((j) => j.status === 'running') ?? false

  // Poll while a job is running
  useListJobsQuery(
    { job_type: 'gmail_sync' },
    { pollingInterval: anyRunning ? POLL_INTERVAL : 0 },
  )

  // When a running job finishes, refetch invoices
  useEffect(() => {
    if (prevRunning.current && !anyRunning) {
      dispatch(api.util.invalidateTags(['Invoices']))
    }
    prevRunning.current = anyRunning
  }, [anyRunning, dispatch])

  const handleSync = () => {
    triggerJob({ job_type: 'gmail_sync' })
  }

  return (
    <Stack>
      <Group justify="space-between">
        <Title order={2}>Collection</Title>
        <Button
          leftSection={<IconMailForward size={18} />}
          onClick={handleSync}
          loading={triggering}
        >
          Sync Gmail
        </Button>
      </Group>

      <Title order={4}>Job History</Title>

      {isLoading && <CollectionSkeleton />}

      {error && (
        <Alert icon={<IconAlertCircle size={16} />} color="red" title="Error">
          Failed to load jobs.
        </Alert>
      )}

      {data && data.items.length === 0 && (
        <Text c="dimmed">No sync jobs yet. Click "Sync Gmail" to start.</Text>
      )}

      {data && data.items.length > 0 && (
        <Table striped>
          <Table.Thead>
            <Table.Tr>
              <Table.Th>Started</Table.Th>
              <Table.Th>Status</Table.Th>
              <Table.Th>Finished</Table.Th>
              <Table.Th>Summary</Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {data.items.map((job) => (
              <Table.Tr key={job.id}>
                <Table.Td>{new Date(job.started_at).toLocaleString()}</Table.Td>
                <Table.Td>
                  <Badge color={STATUS_COLORS[job.status] ?? 'gray'}>
                    {job.status}
                  </Badge>
                </Table.Td>
                <Table.Td>
                  {job.finished_at
                    ? new Date(job.finished_at).toLocaleString()
                    : '—'}
                </Table.Td>
                <Table.Td>
                  <JobSummary summary={job.summary} status={job.status} />
                </Table.Td>
              </Table.Tr>
            ))}
          </Table.Tbody>
        </Table>
      )}
    </Stack>
  )
}
