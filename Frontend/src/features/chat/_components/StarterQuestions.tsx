import {
  Stack,
  Group,
  Button,
  Text,
  Skeleton,
} from '@mantine/core'
import { useChatSuggestionsQuery } from '../../../store/chatApi.ts'

const FALLBACK_QUESTIONS = [
  'What are my top 5 vendors by spend?',
  'Show me this month\'s expenses vs last month.',
  'Are there any unmatched transactions?',
]

export function StarterQuestions({
  onSelect,
}: {
  onSelect: (question: string) => void
}) {
  const { data, isLoading } = useChatSuggestionsQuery()
  const questions = data?.questions ?? FALLBACK_QUESTIONS

  return (
    <Stack align="center" justify="center" py="xl">
      <Text c="dimmed" size="lg">Ask anything about your expenses</Text>
      <Group>
        {isLoading
          ? Array.from({ length: 3 }).map((_, i) => (
              <Skeleton key={i} height={30} width={200} radius="xl" />
            ))
          : questions.map((q) => (
              <Button
                key={q}
                variant="light"
                size="xs"
                onClick={() => onSelect(q)}
              >
                {q}
              </Button>
            ))}
      </Group>
    </Stack>
  )
}
