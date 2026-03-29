import { useState } from 'react'
import {
  Title,
  Stack,
  Text,
  Alert,
  Group,
  Button,
} from '@mantine/core'
import { Dropzone } from '@mantine/dropzone'
import '@mantine/dropzone/styles.css'
import { IconUpload, IconFileSpreadsheet, IconX, IconAlertCircle } from '@tabler/icons-react'
import { notifications } from '@mantine/notifications'
import { useUploadStatementMutation } from '../../../store/reconciliationApi.ts'
import { useNavigate } from 'react-router-dom'

const ACCEPTED_MIME = [
  'text/csv',
  'application/vnd.ms-excel',
  'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
  'application/octet-stream',
]

export function StatementUploadPage() {
  const navigate = useNavigate()
  const [uploadStatement, { isLoading }] = useUploadStatementMutation()
  const [result, setResult] = useState<{ transactions_parsed: number; period: string } | null>(null)

  const handleDrop = async (files: File[]) => {
    const file = files[0]
    if (!file) return

    const formData = new FormData()
    formData.append('file', file)

    try {
      const res = await uploadStatement(formData).unwrap()
      setResult(res)
      notifications.show({
        title: 'Upload successful',
        message: `${res.transactions_parsed} transactions parsed for period ${res.period}`,
        color: 'green',
      })
    } catch {
      notifications.show({
        title: 'Upload failed',
        message: 'Could not process the statement file.',
        color: 'red',
      })
    }
  }

  return (
    <Stack>
      <Title order={2}>Upload Bank Statement</Title>
      <Text c="dimmed">
        Supported formats: XLS, XLSX, CSV, MT940, CAMT.053
      </Text>

      <Dropzone
        onDrop={handleDrop}
        loading={isLoading}
        accept={ACCEPTED_MIME}
        maxFiles={1}
        maxSize={10 * 1024 * 1024}
      >
        <Group justify="center" gap="xl" mih={160} style={{ pointerEvents: 'none' }}>
          <Dropzone.Accept>
            <IconUpload size={48} stroke={1.5} />
          </Dropzone.Accept>
          <Dropzone.Reject>
            <IconX size={48} stroke={1.5} />
          </Dropzone.Reject>
          <Dropzone.Idle>
            <IconFileSpreadsheet size={48} stroke={1.5} />
          </Dropzone.Idle>

          <div>
            <Text size="lg" inline>
              Drag a statement file here or click to browse
            </Text>
            <Text size="sm" c="dimmed" inline mt={7}>
              File should not exceed 10 MB
            </Text>
          </div>
        </Group>
      </Dropzone>

      {result && (
        <Alert icon={<IconAlertCircle size={16} />} color="green" title="Statement processed">
          <Text>
            {result.transactions_parsed} transactions parsed for period <strong>{result.period}</strong>.
          </Text>
          <Group mt="sm">
            <Button
              size="xs"
              onClick={() => navigate(`/reconciliation/matches?period=${result.period}`)}
            >
              Run matching
            </Button>
          </Group>
        </Alert>
      )}
    </Stack>
  )
}
