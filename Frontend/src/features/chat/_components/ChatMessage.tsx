import {
  Paper,
  Text,
  Loader,
  Badge,
  Group,
  TypographyStylesProvider,
} from '@mantine/core'
import Markdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import type { LocalMessage } from '../index.tsx'

export function ChatMessage({
  msg,
  isStreaming,
  isLast,
  onInvoiceClick,
}: {
  msg: LocalMessage
  isStreaming: boolean
  isLast: boolean
  onInvoiceClick: (id: string) => void
}) {
  const showLoader = isStreaming && isLast && msg.role === 'assistant' && !msg.content

  return (
    <Paper
      p="sm"
      radius="md"
      withBorder={msg.role === 'assistant'}
      bg={msg.role === 'user' ? 'var(--mantine-color-blue-light)' : undefined}
      maw="80%"
      ml={msg.role === 'user' ? 'auto' : undefined}
    >
      <Text size="xs" c="dimmed" mb={4}>
        {msg.role === 'user' ? 'You' : 'OpenReconFi'}
      </Text>

      {showLoader ? (
        <Loader size="xs" type="dots" />
      ) : msg.role === 'assistant' ? (
        <TypographyStylesProvider>
          <Markdown remarkPlugins={[remarkGfm]}>{msg.content}</Markdown>
        </TypographyStylesProvider>
      ) : (
        <Text style={{ whiteSpace: 'pre-wrap' }}>{msg.content}</Text>
      )}

      {msg.retrieved_invoice_ids && msg.retrieved_invoice_ids.length > 0 && (
        <Group mt="xs" gap="xs">
          {msg.retrieved_invoice_ids.map((invId) => (
            <Badge
              key={invId}
              variant="outline"
              style={{ cursor: 'pointer' }}
              onClick={() => onInvoiceClick(invId)}
            >
              Invoice {invId.slice(0, 8)}...
            </Badge>
          ))}
        </Group>
      )}
    </Paper>
  )
}
