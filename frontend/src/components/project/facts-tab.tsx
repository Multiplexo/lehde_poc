import { AlertTriangle, CircleCheck, CircleDashed, ShieldCheck } from 'lucide-react'
import { SourceChip } from '@/components/source/source-chip'
import { Badge } from '@/components/ui/badge'
import type { Fact, ProjectAnalysis } from '@/lib/api'

function StatusBadge({ fact }: { fact: Fact }) {
  if (fact.status === 'conflict') return <Badge variant="outline" className="border-critical/40 text-critical"><AlertTriangle aria-hidden="true" />widersprüchlich</Badge>
  if (fact.status === 'not_found') return <Badge variant="outline" className="text-muted-foreground"><CircleDashed aria-hidden="true" />nicht gefunden</Badge>
  return <Badge variant="outline" className="border-ok/40 text-ok"><CircleCheck aria-hidden="true" />belegt</Badge>
}

function FactCard({ fact }: { fact: Fact }) {
  return (
    <article className="panel space-y-3 p-4">
      <div className="flex items-start justify-between gap-3">
        <h3 className="font-medium">{fact.label}</h3>
        <StatusBadge fact={fact} />
      </div>
      {fact.status === 'not_found' ? (
        <p className="text-sm text-muted-foreground">In den Unterlagen nicht gefunden. Wird als Rückfrage vorgeschlagen.</p>
      ) : <>
        <p className="text-sm">{fact.value}</p>
        <details className="group" open={fact.status === 'conflict' || fact.claims.length <= 2}>
          <summary className="cursor-pointer text-xs text-muted-foreground select-none">{fact.claims.length} {fact.claims.length === 1 ? 'Beleg' : 'Belege'}</summary>
          <ul className="mt-2 space-y-2.5">
            {fact.claims.map((claim) => (
              <li key={claim.id} className="space-y-1">
                <p className="text-sm">{claim.value}</p>
                <blockquote className="quote text-xs">„{claim.source.quote}“</blockquote>
                <SourceChip source={claim.source} label={fact.label} />
              </li>
            ))}
          </ul>
        </details>
      </>}
    </article>
  )
}

/** US-3: fact catalog with a source for every value; missing values are never guessed. */
export function FactsTab({ analysis }: { analysis: ProjectAnalysis }) {
  const groups = [...new Set(analysis.facts.map((fact) => fact.group))]
  const found = analysis.facts.filter((fact) => fact.status !== 'not_found').length
  return (
    <div className="space-y-6">
      <p className="flex flex-wrap items-center gap-x-2 gap-y-1 text-sm text-muted-foreground">
        <ShieldCheck aria-hidden="true" className="size-4 text-ok" />
        {found} von {analysis.facts.length} Katalogfeldern belegt · {analysis.stats.claims_found} Aussagen mit Zitat gefunden
        {analysis.stats.claims_dropped ? ` · ${analysis.stats.claims_dropped} Aussagen ohne auffindbares Zitat verworfen` : ''}
      </p>
      {groups.map((group) => (
        <section key={group} aria-label={group} className="space-y-3">
          <h2 className="page-eyebrow">{group}</h2>
          <div className="grid gap-3 md:grid-cols-2 2xl:grid-cols-3">
            {analysis.facts.filter((fact) => fact.group === group).map((fact) => <FactCard key={fact.key} fact={fact} />)}
          </div>
        </section>
      ))}
    </div>
  )
}
