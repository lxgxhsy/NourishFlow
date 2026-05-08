export interface CitationResponse {
  chunk_id: string
  content: string
  section_title: string | null
  page_number: number | null
  article: {
    title: string
    source_org: string
    pub_year: number | null
    tier: number
  }
}

export async function fetchCitation(chunkId: string): Promise<CitationResponse> {
  const res = await fetch(`/api/citations/${chunkId}`)
  if (!res.ok) throw new Error(`${res.status}`)
  return res.json()
}

export interface ChatCallbacks {
  onStart: (conversationId: string) => void
  onDelta: (text: string) => void
  onDone: (data: { cited_chunk_ids: string[]; model: string }) => void
  onError: (error: string) => void
}

export async function streamChat(
  message: string,
  conversationId: string | null,
  callbacks: ChatCallbacks,
): Promise<void> {
  const res = await fetch("/api/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ conversation_id: conversationId, message }),
  })

  if (!res.ok) {
    callbacks.onError(`HTTP ${res.status}`)
    return
  }

  const reader = res.body!.getReader()
  const decoder = new TextDecoder()
  let buffer = ""

  while (true) {
    const { done, value } = await reader.read()
    if (done) break

    buffer += decoder.decode(value, { stream: true })

    const parts = buffer.split("\n\n")
    buffer = parts.pop()! // keep incomplete tail

    for (const part of parts) {
      if (!part.trim()) continue

      let event = "message"
      let data = ""

      for (const line of part.split("\n")) {
        if (line.startsWith("event: ")) event = line.slice(7)
        else if (line.startsWith("data: ")) data = line.slice(6)
      }

      if (!data) continue

      try {
        const parsed = JSON.parse(data)
        if (event === "start") callbacks.onStart(parsed.conversation_id)
        else if (event === "message") callbacks.onDelta(parsed.delta)
        else if (event === "done") callbacks.onDone(parsed)
        else if (event === "error") callbacks.onError(parsed.error)
      } catch {
        // skip malformed JSON
      }
    }
  }
}
