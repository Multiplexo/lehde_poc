import { useEffect, useLayoutEffect, useRef, useState } from 'react'
import { Document, Page, pdfjs } from 'react-pdf'
import { ChevronLeft, ChevronRight, Info, X } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { useDocumentPages } from '@/hooks/use-projects'
import { documentFileUrl, type SourceRef } from '@/lib/api'
import { useSources } from './source-context'

pdfjs.GlobalWorkerOptions.workerSrc = new URL('pdfjs-dist/build/pdf.worker.min.mjs', import.meta.url).toString()

function useWidth() {
  const ref = useRef<HTMLDivElement>(null)
  const [width, setWidth] = useState(600)
  useLayoutEffect(() => {
    const element = ref.current
    if (!element) return
    const observer = new ResizeObserver(([entry]) => setWidth(Math.floor(entry.contentRect.width)))
    observer.observe(element)
    return () => observer.disconnect()
  }, [])
  return { ref, width }
}

function normalize(text: string): string {
  return text.toLowerCase().replace(/\s+/g, ' ').trim()
}

function PdfView({ projectId, source }: { projectId: string; source: SourceRef }) {
  const { ref, width } = useWidth()
  const [page, setPage] = useState(source.page)
  const [pageCount, setPageCount] = useState(0)
  const highlight = useRef<HTMLDivElement>(null)
  const boxes = page === source.page ? source.boxes : []
  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between gap-2 text-sm">
        <Button size="sm" variant="outline" disabled={page <= 1} onClick={() => setPage(page - 1)} aria-label="Vorherige Seite"><ChevronLeft aria-hidden="true" /></Button>
        <span>Seite {page}{pageCount ? ` von ${pageCount}` : ''}</span>
        <Button size="sm" variant="outline" disabled={!pageCount || page >= pageCount} onClick={() => setPage(page + 1)} aria-label="Nächste Seite"><ChevronRight aria-hidden="true" /></Button>
      </div>
      <div ref={ref} className="min-w-0">
        <Document file={documentFileUrl(projectId, source.document_id)} onLoadSuccess={(pdf) => setPageCount(pdf.numPages)}
          loading={<p role="status" className="p-4 text-sm">PDF wird geladen …</p>} error={<p role="alert" className="p-4 text-sm text-destructive">PDF konnte nicht geladen werden.</p>}>
          <div className="relative border bg-white shadow-sm">
            <Page pageNumber={page} width={width} renderAnnotationLayer={false} renderTextLayer={false}
              onRenderSuccess={() => highlight.current?.scrollIntoView({ block: 'center', behavior: 'smooth' })}
              loading={<p role="status" className="p-4 text-sm">Seite wird geladen …</p>} />
            {boxes.map((box, index) => (
              <div key={index} ref={index === 0 ? highlight : undefined} aria-hidden="true"
                className="pointer-events-none absolute rounded-sm bg-brand-accent/35 outline-2 outline-brand-accent mix-blend-multiply"
                style={{ left: `${box.x * 100}%`, top: `${box.y * 100}%`, width: `${box.width * 100}%`, height: `${box.height * 100}%` }} />
            ))}
          </div>
        </Document>
      </div>
    </div>
  )
}

function TextView({ projectId, source }: { projectId: string; source: SourceRef }) {
  const pages = useDocumentPages(projectId, source.document_id)
  const quote = normalize(source.quote)
  const page = pages.data?.pages.find((item) => item.number === source.page)
  if (pages.isPending) return <p role="status" className="text-sm">Text wird geladen …</p>
  if (pages.isError) return <p role="alert" className="text-sm text-destructive">{pages.error.message}</p>
  return (
    <div className="space-y-2 rounded-md border bg-white p-4 text-sm leading-relaxed">
      {page?.lines.map((line, index) => {
        const text = normalize(line.text)
        const hit = text.length > 3 && (quote.includes(text) || text.includes(quote))
        return <p key={index} className={hit ? 'rounded bg-brand-accent/35 px-1' : undefined}>{line.text}</p>
      })}
    </div>
  )
}

/** Side panel with the source page and the quote marked (US-3: click on source). */
export default function SourceDrawer() {
  const { projectId, documents, names, selected, close } = useSources()
  useEffect(() => {
    function onKey(event: KeyboardEvent) { if (event.key === 'Escape') close() }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [close])
  if (!selected) return null
  const { source, label } = selected
  const document = documents.get(source.document_id)
  const isPdf = document?.content_type === 'application/pdf'
  return (
    <aside role="complementary" aria-label="Fundstelle"
      className="fixed inset-y-0 right-0 z-40 flex w-full flex-col border-l bg-background shadow-2xl sm:w-[min(760px,55vw)]">
      <div className="flex items-start gap-3 border-b bg-card px-5 py-4">
        <div className="min-w-0 flex-1">
          <p className="page-eyebrow">Fundstelle{label ? ` · ${label}` : ''}</p>
          <p className="truncate font-medium">{names.get(source.document_id) ?? 'Dokument'}</p>
          <p className="truncate text-xs text-muted-foreground">{document?.filename}</p>
        </div>
        <Button size="icon" variant="ghost" onClick={close} aria-label="Fundstelle schließen"><X aria-hidden="true" /></Button>
      </div>
      <div className="flex-1 space-y-4 overflow-y-auto p-5">
        {source.quote ? <blockquote className="quote not-italic">„{source.quote}“</blockquote> : null}
        {!source.verified ? (
          <p className="flex gap-2 rounded-md bg-warn/10 p-3 text-xs text-warn"><Info aria-hidden="true" className="size-4 shrink-0" />Aus dem Planbild gelesen; die Textstelle ließ sich nicht im Text des Dokuments finden. Bitte am Plan prüfen.</p>
        ) : isPdf && source.boxes.length === 0 ? (
          <p className="flex gap-2 rounded-md bg-muted p-3 text-xs text-muted-foreground"><Info aria-hidden="true" className="size-4 shrink-0" />Für diese Stelle liegt keine Markierung vor; das Zitat steht auf der angezeigten Seite.</p>
        ) : null}
        {isPdf ? <PdfView key={`${source.document_id}:${source.page}:${source.quote}`} projectId={projectId} source={source} /> : <TextView projectId={projectId} source={source} />}
      </div>
    </aside>
  )
}
