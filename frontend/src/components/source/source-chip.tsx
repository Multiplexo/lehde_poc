import { FileSearch } from 'lucide-react'
import type { SourceRef } from '@/lib/api'
import { cn } from '@/lib/utils'
import { useSources } from './source-context'

/** Clickable reference "Document, p. 2" that opens the page with the quote marked. */
export function SourceChip({ source, label, className }: { source: SourceRef; label?: string; className?: string }) {
  const { names, open, selected } = useSources()
  const name = names.get(source.document_id) ?? 'Dokument'
  const active = selected?.source === source
  return (
    <button type="button" onClick={() => open({ source, label })} title={`„${source.quote}“`}
      className={cn('inline-flex max-w-full items-center gap-1.5 rounded-md border px-2 py-0.5 text-xs text-muted-foreground hover:border-brand hover:text-foreground',
        active && 'border-brand bg-accent text-foreground', className)}>
      <FileSearch aria-hidden="true" className="size-3.5 shrink-0" />
      <span className="truncate">{name}, S. {source.page}</span>
    </button>
  )
}
