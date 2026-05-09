import { useState } from "react"
import ReactMarkdown from "react-markdown"
import remarkGfm from "remark-gfm"
import { Badge } from "@/components/ui/badge"
import { CitationDialog } from "@/components/CitationDialog"

interface Props {
  role: "user" | "assistant"
  content: string
  isError?: boolean
}

const CHUNK_ID_RE = /[\[【]chunk_id:([0-9a-f-]{36})[\]】]/g

function renderTextWithBadges(
  text: string,
  onBadgeClick: (id: string) => void,
): React.ReactNode[] {
  const segments: React.ReactNode[] = []
  let lastIndex = 0
  let match: RegExpExecArray | null

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

function transformChildren(
  children: React.ReactNode,
  onBadgeClick: (id: string) => void,
): React.ReactNode {
  if (typeof children === "string") {
    return renderTextWithBadges(children, onBadgeClick)
  }

  if (Array.isArray(children)) {
    return children.map((child, index) =>
      typeof child === "string" ? (
        <span key={index}>{renderTextWithBadges(child, onBadgeClick)}</span>
      ) : (
        child
      ),
    )
  }

  return children
}

function markdownComponents(onBadgeClick: (id: string) => void) {
  return {
    p: ({ children }: { children?: React.ReactNode }) => (
      <p className="mb-2 last:mb-0">{transformChildren(children, onBadgeClick)}</p>
    ),
    strong: ({ children }: { children?: React.ReactNode }) => (
      <strong className="font-semibold">{transformChildren(children, onBadgeClick)}</strong>
    ),
    em: ({ children }: { children?: React.ReactNode }) => (
      <em className="italic">{transformChildren(children, onBadgeClick)}</em>
    ),
    ul: ({ children }: { children?: React.ReactNode }) => (
      <ul className="list-disc pl-5 my-2 space-y-1">{children}</ul>
    ),
    ol: ({ children }: { children?: React.ReactNode }) => (
      <ol className="list-decimal pl-5 my-2 space-y-1">{children}</ol>
    ),
    li: ({ children }: { children?: React.ReactNode }) => (
      <li>{transformChildren(children, onBadgeClick)}</li>
    ),
    h1: ({ children }: { children?: React.ReactNode }) => (
      <h3 className="text-base font-semibold mt-3 mb-1">{children}</h3>
    ),
    h2: ({ children }: { children?: React.ReactNode }) => (
      <h3 className="text-base font-semibold mt-3 mb-1">{children}</h3>
    ),
    h3: ({ children }: { children?: React.ReactNode }) => (
      <h3 className="text-sm font-semibold mt-2 mb-1">{children}</h3>
    ),
    code: ({ children }: { children?: React.ReactNode }) => (
      <code className="px-1 py-0.5 bg-muted rounded text-xs">{children}</code>
    ),
    a: ({ href, children }: { href?: string; children?: React.ReactNode }) => (
      <a href={href} target="_blank" rel="noreferrer" className="underline">
        {children}
      </a>
    ),
  }
}

export function MessageBubble({ role, content, isError }: Props) {
  const [openChunkId, setOpenChunkId] = useState<string | null>(null)
  const isUser = role === "user"

  return (
    <>
      <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
        <div
          className={`max-w-[80%] rounded-2xl px-4 py-2.5 text-sm leading-relaxed ${
            isUser
              ? "bg-primary text-primary-foreground"
              : isError
                ? "bg-destructive/10 text-destructive"
                : "bg-muted"
          }`}
        >
          {isUser || isError ? (
            <span className="whitespace-pre-wrap">{content}</span>
          ) : (
            <ReactMarkdown
              remarkPlugins={[remarkGfm]}
              components={markdownComponents(setOpenChunkId)}
            >
              {content}
            </ReactMarkdown>
          )}
        </div>
      </div>

      {openChunkId && (
        <CitationDialog
          chunkId={openChunkId}
          open
          onOpenChange={(open) => {
            if (!open) setOpenChunkId(null)
          }}
        />
      )}
    </>
  )
}
