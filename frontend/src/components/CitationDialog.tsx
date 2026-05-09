import { useEffect, useState } from "react"
import { fetchCitation, type CitationResponse } from "@/lib/api"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Badge } from "@/components/ui/badge"
import { Separator } from "@/components/ui/separator"

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
      <DialogContent className="sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 text-lg">
            {loading ? "加载中..." : error ? "引用详情" : data?.article.title}
            {data && (
              <Badge variant="secondary" className="text-xs">
                Tier {data.article.tier}
              </Badge>
            )}
          </DialogTitle>
          {data && (
            <p className="text-xs text-muted-foreground">
              {data.article.source_org}
              {data.article.pub_year ? ` · ${data.article.pub_year}` : ""}
              {data.page_number != null ? ` · 第 ${data.page_number} 页` : ""}
              {data.section_title ? ` · ${data.section_title}` : ""}
            </p>
          )}
        </DialogHeader>

        <Separator />

        {loading && (
          <p className="text-muted-foreground text-sm">加载中...</p>
        )}
        {error && (
          <p className="text-destructive text-sm">
            {error}（chunk_id: {chunkId}）
          </p>
        )}
        {data && (
          <div className="max-h-[60vh] overflow-y-auto">
            <div className="bg-muted/50 rounded-lg p-4 text-sm leading-relaxed">
              {data.content}
            </div>
          </div>
        )}
      </DialogContent>
    </Dialog>
  )
}
