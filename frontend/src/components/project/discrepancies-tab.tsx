import { useState } from 'react'
import { ArrowLeftRight, CircleCheck, FileStack } from 'lucide-react'
import { SourceChip } from '@/components/source/source-chip'
import { useSources } from '@/components/source/source-context'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { NativeSelect, NativeSelectOption } from '@/components/ui/native-select'
import { Textarea } from '@/components/ui/textarea'
import { useUpdateDiscrepancy } from '@/hooks/use-projects'
import type { Discrepancy, DiscrepancySide, DiscrepancyStatus, Project, Recipient, Severity } from '@/lib/api'
import { discrepancyStatuses, discrepancyStatusLabels, recipientLabels, recipients, severityLabels } from '@/lib/labels'
import { cn } from '@/lib/utils'

const severityStyle: Record<Severity, string> = {
  red: 'bg-critical',
  yellow: 'bg-warn',
}

function Side({ side, label }: { side: DiscrepancySide; label: string }) {
  const { names } = useSources()
  return (
    <div className="min-w-0 flex-1 space-y-1.5 rounded-lg border bg-background p-3">
      <p className="page-eyebrow mb-0">{label} · {names.get(side.document_id) ?? 'Dokument'}</p>
      <p className="text-sm font-medium">{side.value}</p>
      {side.source?.quote ? <blockquote className="quote text-xs">„{side.source.quote}“</blockquote> : null}
      {side.source ? <SourceChip source={side.source} /> : null}
    </div>
  )
}

function QuestionField({ value, disabled, onSave }: { value: string; disabled: boolean; onSave: (value: string) => void }) {
  const [question, setQuestion] = useState(value)
  return (
    <label className="space-y-1 text-xs font-medium">Vorgeschlagene Rückfrage
      <Textarea value={question} disabled={disabled} rows={2} className="text-sm font-normal"
        onChange={(event) => setQuestion(event.target.value)}
        onBlur={() => { if (question.trim().length >= 3 && question.trim() !== value) onSave(question.trim()) }} />
    </label>
  )
}

function DiscrepancyCard({ project, item }: { project: Project; item: Discrepancy }) {
  const update = useUpdateDiscrepancy(project.id)
  const busy = update.isPending || project.status === 'processing'
  const done = item.status === 'done'
  return (
    <article className={cn('panel overflow-hidden', done && 'opacity-70')}>
      <div className="flex">
        <span aria-hidden="true" className={cn('w-1.5 shrink-0', done ? 'bg-ok' : severityStyle[item.severity])} />
        <div className="min-w-0 flex-1 space-y-4 p-4">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div className="min-w-0">
              <h3 className="font-medium">{item.title}</h3>
              <p className="text-sm text-muted-foreground">{item.explanation}</p>
            </div>
            <div className="flex flex-wrap gap-1.5">
              <Badge variant="outline" className={item.severity === 'red' ? 'border-critical/40 text-critical' : 'border-warn/40 text-warn'}>
                <span aria-hidden="true" className={cn('size-2 rounded-full', severityStyle[item.severity])} />{severityLabels[item.severity]}
              </Badge>
              {item.kind === 'planstand' ? <Badge variant="secondary"><FileStack aria-hidden="true" />Planstand (regelbasiert)</Badge> : null}
            </div>
          </div>
          <div className="flex flex-col items-stretch gap-2 lg:flex-row">
            <Side side={item.side_a} label="Quelle A" />
            {item.side_b ? <>
              <ArrowLeftRight aria-hidden="true" className="size-4 shrink-0 self-center text-muted-foreground" />
              <Side side={item.side_b} label="Quelle B" />
            </> : null}
          </div>
          <div className="grid gap-3 border-t pt-3 md:grid-cols-[220px_220px_1fr]">
            <label className="space-y-1 text-xs font-medium">Folgeaktion
              <NativeSelect value={item.status} disabled={busy} className="w-full"
                onChange={(event) => update.mutate({ id: item.id, data: { status: event.target.value as DiscrepancyStatus } })}>
                {discrepancyStatuses.map((status) => <NativeSelectOption key={status} value={status}>{discrepancyStatusLabels[status]}</NativeSelectOption>)}
              </NativeSelect>
            </label>
            <label className="space-y-1 text-xs font-medium">Empfänger
              <NativeSelect value={item.recipient} disabled={busy} className="w-full"
                onChange={(event) => update.mutate({ id: item.id, data: { recipient: event.target.value as Recipient } })}>
                {recipients.map((recipient) => <NativeSelectOption key={recipient} value={recipient}>{recipientLabels[recipient]}</NativeSelectOption>)}
              </NativeSelect>
            </label>
            <QuestionField key={item.question} value={item.question} disabled={busy}
              onSave={(question) => update.mutate({ id: item.id, data: { question } })} />
          </div>
          {update.error ? <p role="alert" className="text-xs text-destructive">{update.error.message}</p> : null}
        </div>
      </div>
    </article>
  )
}

type Filter = 'open' | 'all'

/** US-4: contradictions between documents with both quotes, severity and a follow-up. */
export function DiscrepanciesTab({ project, onShowQuestions }: { project: Project; onShowQuestions: () => void }) {
  const [filter, setFilter] = useState<Filter>('open')
  const items = project.analysis?.discrepancies ?? []
  const visible = filter === 'open' ? items.filter((item) => item.status !== 'done') : items
  const red = items.filter((item) => item.severity === 'red' && item.status !== 'done').length
  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-3">
        <p className="text-sm text-muted-foreground">
          Jede Abweichung braucht eine Folgeaktion: Rückfrage an Architekt oder Bauherr, Annahme im Angebot oder erledigt.
          {red ? <strong className="ml-1 text-critical">{red} kritisch offen.</strong> : null}
        </p>
        <div className="ml-auto flex gap-2">
          <NativeSelect aria-label="Filter" value={filter} onChange={(event) => setFilter(event.target.value as Filter)}>
            <NativeSelectOption value="open">Nur offene</NativeSelectOption>
            <NativeSelectOption value="all">Alle ({items.length})</NativeSelectOption>
          </NativeSelect>
          <Button variant="outline" onClick={onShowQuestions}>Zur Rückfrageliste</Button>
        </div>
      </div>
      {visible.length === 0 ? (
        <div className="panel flex flex-col items-center gap-2 p-10 text-center text-sm text-muted-foreground">
          <CircleCheck aria-hidden="true" className="size-8 text-ok" />
          {items.length ? 'Alle Abweichungen sind bearbeitet.' : 'Keine Widersprüche zwischen den Unterlagen gefunden.'}
        </div>
      ) : visible.map((item) => <DiscrepancyCard key={item.id} project={project} item={item} />)}
    </div>
  )
}
