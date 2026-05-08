import { useState } from "react"
import { Badge } from "@/components/ui/badge"
import { CitationDialog } from "@/components/CitationDialog"

interface Props {
  role: "user" | "assistant"
  content: string
  isError?: boolean
}

const CHUNK_ID_RE = /[\[【]chunk_id:([0-9a-f-]{36})[\]】]/g

function renderContent(text: string, onBadgeClick: (id: string) => void) {
  const segments: React.ReactNode[] = []
  let lastIndex = 0
  let match: RegExpExecArray | null

  // Reset regex state
  CHUNK_ID_RE.lastIndex = 0

  while ((match = CHUNK_ID_RE.exec(text)) !== null) {
    if (match.index > lastIndex) {
      segments.push(text.slice(lastIndex, match.index))
    }
    const chunkId = match[1]
    segments.push(
      <Badge
        key={`${chunkId}-${match.index}`}
        variant="secondary"
        className="cursor-pointer text-[10px] px-1.5 mx-0.5 hover:bg-primary hover:text-primary-foreground"
        onClick={() => onBadgeClick(chunkId)}
      >
        {chunkId.slice(0, 8)}
      </Badge>,
    )
    lastIndex = match.index + match[0].length
  }

  if (lastIndex < text.length) {
    segments.push(text.slice(lastIndex))
  }

  return segments
}

export function MessageBubble({ role, content, isError }: Props) {
  const [openChunkId, setOpenChunkId] = useState<string | null>(null)

  const isUser = role === "user"

  return (
    <>
      <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
        <div
          className={`max-w-[80%] rounded-2xl px-4 py-2.5 text-sm leading-relaxed whitespace-pre-wrap ${
            isUser
              ? "bg-primary text-primary-foreground"
              : isError
                ? "bg-destructive/10 text-destructive"
                : "bg-muted"
          }`}
        >
          {isUser || isError ? content : renderContent(content, setOpenChunkId)}
        </div>
      </div>

      {openChunkId && (
        <CitationDialog
          chunkId={openChunkId}
          open
          onOpenChange={(o) => { if (!o) setOpenChunkId(null) }}
        />
      )}
    </>
  )
}
