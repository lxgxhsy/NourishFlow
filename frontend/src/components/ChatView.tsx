import { useState, useRef, useEffect } from "react"
import { streamChat } from "@/lib/api"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import { ScrollArea } from "@/components/ui/scroll-area"
import { MessageBubble } from "@/components/MessageBubble"

interface Message {
  role: "user" | "assistant"
  content: string
  isError?: boolean
}

export function ChatView() {
  const [messages, setMessages] = useState<Message[]>([])
  const [conversationId, setConversationId] = useState<string | null>(null)
  const [input, setInput] = useState("")
  const [isStreaming, setIsStreaming] = useState(false)
  const scrollRef = useRef<HTMLDivElement>(null)

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [messages])

  async function handleSend() {
    const text = input.trim()
    if (!text || isStreaming) return

    setInput("")
    setMessages((prev) => [...prev, { role: "user", content: text }])
    setIsStreaming(true)

    // Add empty assistant message for streaming
    setMessages((prev) => [...prev, { role: "assistant", content: "" }])

    await streamChat(text, conversationId, {
      onStart: (convId) => setConversationId(convId),
      onDelta: (delta) =>
        setMessages((prev) => {
          const last = prev[prev.length - 1]
          return [
            ...prev.slice(0, -1),
            { ...last, content: last.content + delta },
          ]
        }),
      onDone: () => setIsStreaming(false),
      onError: (error) => {
        setMessages((prev) => {
          const last = prev[prev.length - 1]
          if (last.role === "assistant" && last.content === "") {
            return [
              ...prev.slice(0, -1),
              { role: "assistant", content: `错误: ${error}`, isError: true },
            ]
          }
          return [
            ...prev,
            { role: "assistant", content: `错误: ${error}`, isError: true },
          ]
        })
        setIsStreaming(false)
      },
    })
  }

  return (
    <div className="flex flex-col h-full">
      <ScrollArea className="flex-1 overflow-y-auto">
        <div ref={scrollRef} className="p-4 space-y-4">
          {messages.length === 0 && (
            <p className="text-center text-muted-foreground text-sm mt-8">
              问问我关于营养和血糖的问题吧
            </p>
          )}
          {messages.map((msg, i) => (
            <MessageBubble
              key={i}
              role={msg.role}
              content={msg.content}
              isError={msg.isError}
            />
          ))}
          {isStreaming && (
            <div className="flex justify-start">
              <div className="bg-muted rounded-2xl px-4 py-2.5 text-sm">
                <span className="animate-pulse">...</span>
              </div>
            </div>
          )}
        </div>
      </ScrollArea>

      <div className="border-t p-4 flex gap-2">
        <Input
          value={input}
          onChange={(e) => setInput((e.target as HTMLInputElement).value)}
          onKeyDown={(e) => { if (e.key === "Enter") handleSend() }}
          placeholder="输入消息..."
          disabled={isStreaming}
        />
        <Button onClick={handleSend} disabled={isStreaming || !input.trim()}>
          发送
        </Button>
      </div>
    </div>
  )
}
