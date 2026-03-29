import {
  Group,
  TextInput,
  ActionIcon,
} from '@mantine/core'
import { IconSend } from '@tabler/icons-react'

export function ChatInput({
  input,
  onInputChange,
  onSubmit,
  disabled,
}: {
  input: string
  onInputChange: (value: string) => void
  onSubmit: (e: React.FormEvent) => void
  disabled: boolean
}) {
  return (
    <form onSubmit={onSubmit}>
      <Group>
        <TextInput
          flex={1}
          placeholder="Ask about your expenses..."
          value={input}
          onChange={(e) => onInputChange(e.currentTarget.value)}
          disabled={disabled}
        />
        <ActionIcon
          type="submit"
          size="lg"
          variant="filled"
          disabled={!input.trim() || disabled}
        >
          <IconSend size={18} />
        </ActionIcon>
      </Group>
    </form>
  )
}
