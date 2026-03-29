import { Stack, Group, Skeleton, ScrollArea } from '@mantine/core'

export function ChatSkeleton() {
  return (
    <Stack h="calc(100vh - 120px)">
      <Group justify="space-between">
        <Skeleton h={28} w={180} />
        <Skeleton h={36} w={80} radius="sm" />
      </Group>

      <ScrollArea flex={1}>
        <Stack gap="md" p="xs">
          {/* User message */}
          <Skeleton h={48} w="60%" ml="auto" radius="md" />
          {/* Assistant message */}
          <Skeleton h={80} w="75%" radius="md" />
          {/* User message */}
          <Skeleton h={40} w="50%" ml="auto" radius="md" />
          {/* Assistant message */}
          <Skeleton h={120} w="70%" radius="md" />
        </Stack>
      </ScrollArea>

      <Skeleton h={42} radius="sm" />
    </Stack>
  )
}
