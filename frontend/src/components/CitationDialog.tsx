import { useEffect, useState } from "react"
import { fetchCitation, type CitationResponse } from "@/lib/api"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog"

interface Props {
  chunkId: string
  open: boolean
  onOpenChange: (open: boolean) => void
}

export function CitationDialog({ chunkId, open, onOpenChange }: Props) {
  const [data, setData] = useState<CitationResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (!open) return
    setLoading(true)
    setError(null)
    setData(null)
    fetchCitation(chunkId)
      .then(setData)
      .catch(() => setError("加载失败"))
      .finally(() => setLoading(false))
  }, [open, chunkId])

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>引用原文</DialogTitle>
          <DialogDescription>
            {data?.article.title}
            {data?.article.pub_year ? ` (${data.article.pub_year})` : ""}
            {" — "}
            {data?.article.source_org}
            {" · tier "}
            {data?.article.tier}
          </DialogDescription>
        </DialogHeader>

        {loading && <p className="text-muted-foreground">加载中...</p>}
        {error && (
          <p className="text-destructive">
            {error}（chunk_id: {chunkId}）
          </p>
        )}
        {data && (
          <div className="space-y-2">
            {data.section_title && (
              <p className="text-xs text-muted-foreground">
                章节: {data.section_title}
                {data.page_number != null ? ` · 第 ${data.page_number} 页` : ""}
              </p>
            )}
            {data.page_number != null && !data.section_title && (
              <p className="text-xs text-muted-foreground">
                第 {data.page_number} 页
              </p>
            )}
            <p className="text-sm leading-relaxed whitespace-pre-wrap">
              {data.content}
            </p>
          </div>
        )}
      </DialogContent>
    </Dialog>
  )
}
