import { useMutation, useQueryClient } from '@tanstack/react-query'
import { CircleAlert, CircleCheck, CircleDashed, CircleMinus, Info, MessageSquarePlus, RefreshCw } from 'lucide-react'
import { SourceChip } from '@/components/source/source-chip'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { projectKeys, useUpdateQuestions } from '@/hooks/use-projects'
import { api, type CheckArea, type CheckFinding, type CheckStatus, type Project } from '@/lib/api'
import { checkAreaLabels, checkStatusLabels, formatDate, recipientLabels } from '@/lib/labels'

const statusStyle: Record<CheckStatus, { className: string; icon: typeof CircleCheck }> = {
  critical: { className: 'border-critical/40 text-critical', icon: CircleAlert },
  note: { className: 'border-warn/40 text-warn', icon: Info },
  missing: { className: 'text-muted-foreground', icon: CircleDashed },
  ok: { className: 'border-ok/40 text-ok', icon: CircleCheck },
  not_applicable: { className: 'text-muted-foreground', icon: CircleMinus },
}
const order: CheckStatus[] = ['critical', 'note', 'missing', 'ok', 'not_applicable']

function Finding({ project, finding }: { project: Project; finding: CheckFinding }) {
  const save = useUpdateQuestions(project.id)
  const style = statusStyle[finding.status]
  const Icon = style.icon
  const questionId = `q-check-${finding.rule_id}`
  const taken = project.questions.some((question) => question.id === questionId)
  return (
    <li className="space-y-2 px-4 py-3">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <h3 className="font-medium">{finding.title}</h3>
        <Badge variant="outline" className={style.className}><Icon aria-hidden="true" />{checkStatusLabels[finding.status]}</Badge>
      </div>
      <p className="text-sm">{finding.finding}</p>
      {finding.sources.length ? (
        <div className="space-y-1.5">
          {finding.sources.map((source, index) => (
            <div key={index} className="space-y-1">
              <blockquote className="quote text-xs">„{source.quote}“</blockquote>
              <SourceChip source={source} label={finding.title} />
            </div>
          ))}
        </div>
      ) : null}
      {finding.status !== 'ok' && finding.status !== 'not_applicable' ? (
        <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
          <span>Empfänger: {recipientLabels[finding.recipient]} · Folgeaktion: {finding.action}</span>
          {finding.question ? (
            <Button size="xs" variant="outline" disabled={taken || save.isPending} className="ml-auto"
              onClick={() => save.mutate([...project.questions, {
                id: questionId, text: finding.question!, recipient: finding.recipient, included: true, discrepancy_id: null, fact_key: null, sources: finding.sources,
              }])}>
              <MessageSquarePlus aria-hidden="true" />{taken ? 'In Rückfrageliste' : 'Als Rückfrage übernehmen'}
            </Button>
          ) : null}
        </div>
      ) : null}
    </li>
  )
}

/** Check agents for contract/VOB, fire safety, soil and change orders. */
export function ChecksTab({ project }: { project: Project }) {
  const client = useQueryClient()
  const run = useMutation({
    mutationFn: () => api.runChecks(project.id),
    onSuccess: (updated) => client.setQueryData(projectKeys.detail(project.id), updated),
  })
  const areas = Object.keys(checkAreaLabels) as CheckArea[]
  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-3">
        <p className="max-w-3xl text-sm text-muted-foreground">
          Prüfung gegen eine interne Checkliste mit Schwellenwerten, nicht gegen Normtexte (VOB/DIN-Lizenz ist noch offen). Bewertungen ohne belegbares Zitat werden als „nicht geregelt“ geführt.
          {project.checks_at ? ` Stand ${formatDate(project.checks_at)}.` : ''}
        </p>
        <Button variant="outline" className="ml-auto" disabled={project.status === 'processing' || run.isPending} onClick={() => run.mutate()}>
          <RefreshCw aria-hidden="true" />Prüfung neu ausführen
        </Button>
      </div>
      {run.error ? <p role="alert" className="text-sm text-destructive">{run.error.message}</p> : null}
      {project.checks.length === 0 ? <p className="panel p-8 text-center text-sm text-muted-foreground">Noch keine Prüfergebnisse.</p> : null}
      <div className="grid gap-4 xl:grid-cols-2">
        {areas.map((area) => {
          const findings = project.checks.filter((item) => item.area === area).sort((a, b) => order.indexOf(a.status) - order.indexOf(b.status))
          if (!findings.length) return null
          const critical = findings.filter((item) => item.status === 'critical').length
          return (
            <section key={area} className="panel" aria-label={checkAreaLabels[area]}>
              <h2 className="flex items-center justify-between border-b px-4 py-3 font-medium">
                {checkAreaLabels[area]}
                {critical ? <span className="text-sm text-critical">{critical} kritisch</span> : null}
              </h2>
              <ul className="divide-y">{findings.map((finding) => <Finding key={finding.rule_id} project={project} finding={finding} />)}</ul>
            </section>
          )
        })}
      </div>
    </div>
  )
}
