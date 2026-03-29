import { useState, useRef, useEffect } from 'react'
import { notifications } from '@mantine/notifications'
import { useChatHistoryQuery, useClearChatHistoryMutation } from '../../../store/chatApi.ts'
import type { ChatMessageRead } from '../../../api/types/index.ts'

export interface LocalMessage {
  role: 'user' | 'assistant'
  content: string
  retrieved_invoice_ids?: string[] | null
}

export function useChat() {
  const [input, setInput] = useState('')
  const [streaming, setStreaming] = useState(false)
  const [localMessages, setLocalMessages] = useState<LocalMessage[]>([])
  const viewportRef = useRef<HTMLDivElement>(null)

  const { data: history, isLoading, error, refetch } = useChatHistoryQuery()
  const [clearHistory] = useClearChatHistoryMutation()

  const serverMessages: LocalMessage[] = (history?.items ?? []).map((m: ChatMessageRead) => ({
    role: m.role,
    content: m.content,
    retrieved_invoice_ids: m.retrieved_invoice_ids,
  }))
  const allMessages = localMessages.length > 0 ? localMessages : serverMessages

  useEffect(() => {
    viewportRef.current?.scrollTo({ top: viewportRef.current.scrollHeight, behavior: 'smooth' })
  }, [allMessages.length, streaming])

  useEffect(() => {
    if (history && localMessages.length === 0) {
      setLocalMessages(serverMessages)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [history])

  const sendMessage = async (message: string) => {
    if (!message.trim() || streaming) return

    const userMsg: LocalMessage = { role: 'user', content: message }
    const assistantMsg: LocalMessage = { role: 'assistant', content: '', retrieved_invoice_ids: null }

    setLocalMessages((prev) => [...prev, userMsg, assistantMsg])
    setInput('')
    setStreaming(true)

    try {
      const response = await fetch('/api/chat/message', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message }),
      })

      if (!response.ok) throw new Error('Chat request failed')

      const reader = response.body?.getReader()
      const decoder = new TextDecoder()

      if (!reader) throw new Error('No response body')

      let fullContent = ''
      let retrievedIds: string[] | null = null

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        const chunk = decoder.decode(value, { stream: true })
        const lines = chunk.split('\n')

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = line.slice(6)
            if (data === '[DONE]') continue

            try {
              const parsed = JSON.parse(data)
              if (parsed.content) {
                fullContent += parsed.content
              }
              if (parsed.retrieved_invoice_ids) {
                retrievedIds = parsed.retrieved_invoice_ids
              }
            } catch {
              fullContent += data
            }
          }
        }

        setLocalMessages((prev) => {
          const updated = [...prev]
          updated[updated.length - 1] = {
            role: 'assistant',
            content: fullContent,
            retrieved_invoice_ids: retrievedIds,
          }
          return updated
        })
      }

      refetch()
    } catch {
      notifications.show({ title: 'Error', message: 'Failed to send message.', color: 'red' })
      setLocalMessages((prev) => prev.slice(0, -1))
    } finally {
      setStreaming(false)
    }
  }

  const handleClear = async () => {
    try {
      await clearHistory().unwrap()
      setLocalMessages([])
      notifications.show({ title: 'Cleared', message: 'Chat history cleared.', color: 'green' })
    } catch {
      notifications.show({ title: 'Error', message: 'Failed to clear history.', color: 'red' })
    }
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    sendMessage(input)
  }

  return {
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
  }
}
