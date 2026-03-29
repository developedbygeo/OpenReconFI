import {
  Title,
  Stack,
  Group,
  Button,
  ScrollArea,
  Alert,
  Skeleton,
} from '@mantine/core'
import { IconTrash, IconAlertCircle } from '@tabler/icons-react'
import { useNavigate } from 'react-router-dom'
import { ChatMessage } from './_components/ChatMessage.tsx'
import { ChatInput } from './_components/ChatInput.tsx'
import { StarterQuestions } from './_components/StarterQuestions.tsx'
import { useChat } from './_hooks/useChat.ts'
import { ChatSkeleton } from './_components/ChatSkeleton.tsx'
import { useChatSuggestionsQuery } from '../../store/api.ts'

export type { LocalMessage } from './_hooks/useChat.ts'

function SuggestionChips({ onSelect }: { onSelect: (q: string) => void }) {
  const { data, isLoading } = useChatSuggestionsQuery()

  if (isLoading) {
    return (
      <Group gap="xs" px="xs">
        {Array.from({ length: 3 }).map((_, i) => (
          <Skeleton key={i} height={26} width={180} radius="xl" />
        ))}
      </Group>
    )
  }

  if (!data?.questions?.length) return null

  return (
    <Group gap="xs" px="xs">
      {data.questions.map((q) => (
        <Button
          key={q}
          variant="light"
          size="compact-xs"
          onClick={() => onSelect(q)}
        >
          {q}
        </Button>
      ))}
    </Group>
  )
}

export function ChatPage() {
  const navigate = useNavigate()
  const {
    input,
    setInput,
    streaming,
    allMessages,
    viewportRef,
    isLoading,
    error,
    sendMessage,
    handleClear,
    handleSubmit,
  } = useChat()

  if (isLoading) return <ChatSkeleton />

  if (error) {
    return (
      <Alert icon={<IconAlertCircle size={16} />} color="red" title="Error">
        Failed to load chat history.
      </Alert>
    )
  }

  const showFollowUps = allMessages.length > 0 && !streaming

  return (
    <Stack h="calc(100vh - 120px)">
      <Group justify="space-between">
        <Title order={2}>Expense Chat</Title>
        <Button
          variant="subtle"
          color="red"
          leftSection={<IconTrash size={16} />}
          onClick={handleClear}
          disabled={allMessages.length === 0}
        >
          Clear
        </Button>
      </Group>

      <ScrollArea flex={1} viewportRef={viewportRef}>
        <Stack gap="md" p="xs">
          {allMessages.length === 0 && (
            <StarterQuestions onSelect={sendMessage} />
          )}

          {allMessages.map((msg, i) => (
            <ChatMessage
              key={i}
              msg={msg}
              isStreaming={streaming}
              isLast={i === allMessages.length - 1}
              onInvoiceClick={(id) => navigate(`/invoices/${id}`)}
            />
          ))}

          {showFollowUps && (
            <SuggestionChips onSelect={sendMessage} />
          )}
        </Stack>
      </ScrollArea>

      <ChatInput
        input={input}
        onInputChange={setInput}
        onSubmit={handleSubmit}
        disabled={streaming}
      />
    </Stack>
  )
}
