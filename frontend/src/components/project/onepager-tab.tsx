import { Download } from 'lucide-react'
import { SourceChip } from '@/components/source/source-chip'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { useOnepager } from '@/hooks/use-projects'
import { exportUrl, type Project } from '@/lib/api'

/** US-6: one-pager for the handover to technical office and precast department. */
export function OnepagerTab({ project }: { project: Project }) {
  const onepager = useOnepager(project.id, project.updated_at)
  const claims = new Map((project.analysis?.claims ?? []).map((claim) => [claim.id, claim]))
  const summarySources = (project.analysis?.summary?.claim_ids ?? []).map((id) => claims.get(id)).filter((claim) => claim !== undefined)
  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-3">
        <p className="text-sm text-muted-foreground">Für technisches Büro und Fertigteilabteilung. Offene Punkte kommen aus den nicht erledigten Abweichungen.</p>
        <div className="ml-auto flex gap-2">
          <Button nativeButton={false} render={<a href={exportUrl(project.id, 'onepager.pdf')} download />}><Download aria-hidden="true" />PDF</Button>
          <Button variant="outline" nativeButton={false} render={<a href={exportUrl(project.id, 'onepager.docx')} download />}><Download aria-hidden="true" />DOCX</Button>
        </div>
      </div>
      {onepager.isPending ? <Skeleton className="h-96" /> : null}
      {onepager.isError ? <p role="alert" className="text-sm text-destructive">{onepager.error.message}</p> : null}
      {onepager.data ? (
        <article className="panel mx-auto max-w-4xl space-y-6 p-6 md:p-10">
          <header className="space-y-2 border-b pb-4">
            <p className="page-eyebrow">Projektsteckbrief · Übergabe Kalkulation</p>
            <h2 className="text-2xl font-semibold tracking-tight">{onepager.data.project_name}</h2>
            {onepager.data.summary ? <p className="text-sm leading-relaxed">{onepager.data.summary}</p> : null}
            {summarySources.length ? <div className="flex flex-wrap gap-1.5">{summarySources.map((claim) => <SourceChip key={claim.id} source={claim.source} />)}</div> : null}
          </header>
          <dl className="divide-y">
            {onepager.data.sections.map((section) => (
              <div key={section.label} className="grid gap-1 py-3 md:grid-cols-[200px_1fr]">
                <dt className="text-sm font-medium">{section.label}</dt>
                <dd className="space-y-1">
                  <p className={section.value === 'nicht gefunden' ? 'text-sm text-muted-foreground italic' : 'text-sm whitespace-pre-line'}>{section.value}</p>
                  {section.sources.length ? <p className="text-xs text-muted-foreground">Quelle: {section.sources.join('; ')}</p> : null}
                </dd>
              </div>
            ))}
          </dl>
          <section>
            <h3 className="mb-2 font-medium">Offene Punkte</h3>
            {onepager.data.open_points.length ? (
              <ul className="list-disc space-y-1 pl-5 text-sm">{onepager.data.open_points.map((point) => <li key={point}>{point}</li>)}</ul>
            ) : <p className="text-sm text-muted-foreground">Keine</p>}
          </section>
          <section>
            <h3 className="mb-2 font-medium">Unterlagen</h3>
            <ul className="space-y-0.5 text-sm text-muted-foreground">
              {onepager.data.documents.map((item) => (
                <li key={item.filename}>{item.filename} – {[item.doc_type, item.revision, item.document_date].filter(Boolean).join(', ')}</li>
              ))}
            </ul>
          </section>
        </article>
      ) : null}
    </div>
  )
}
