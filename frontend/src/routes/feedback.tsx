import { useQuery } from '@tanstack/react-query'
import { createFileRoute } from '@tanstack/react-router'
import { Copy, Send } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { api, screenshotUrl, type Feedback } from '@/lib/api'
import { feedbackKindLabels, formatDate, moduleLabels } from '@/lib/labels'

export const Route = createFileRoute('/feedback')({ component: FeedbackPage })

function Entry({ item, all }: { item: Feedback; all: Feedback[] }) {
  const kind = item.triage?.kind ?? item.kind
  const duplicate = item.triage?.duplicate_of ? all.find((entry) => entry.id === item.triage?.duplicate_of) : undefined
  return (
    <li className="grid gap-4 px-5 py-4 md:grid-cols-[1fr_220px]">
      <div className="min-w-0 space-y-2">
        <div className="flex flex-wrap items-center gap-1.5">
          {kind ? <Badge variant={kind === 'bug' ? 'destructive' : 'secondary'}>{feedbackKindLabels[kind]}</Badge> : <Badge variant="outline">wird eingeordnet …</Badge>}
          {item.triage ? <Badge variant="outline">{moduleLabels[item.triage.module] ?? item.triage.module}</Badge> : null}
          {duplicate ? <Badge variant="outline" className="text-warn"><Copy aria-hidden="true" />Duplikat</Badge> : null}
          {item.forwarded_at ? <Badge variant="outline" className="text-ok"><Send aria-hidden="true" />ans Ticketsystem</Badge> : null}
        </div>
        {item.triage?.summary ? <p className="font-medium">{item.triage.summary}</p> : null}
        <p className="text-sm whitespace-pre-line">{item.message}</p>
        {duplicate ? <p className="text-xs text-muted-foreground">Gleiches Anliegen wie: „{duplicate.message.slice(0, 120)}“</p> : null}
        <p className="text-xs text-muted-foreground">
          {formatDate(item.created_at)}{item.user_name ? ` · ${item.user_name}` : ''} · <a href={item.url} className="underline">Seite öffnen</a>
        </p>
      </div>
      {item.has_screenshot ? (
        <a href={screenshotUrl(item.id)} target="_blank" rel="noreferrer" className="block">
          <img src={screenshotUrl(item.id)} alt="Screenshot zum Feedback" loading="lazy" className="max-h-36 w-full rounded-md border object-cover object-top" />
        </a>
      ) : null}
    </li>
  )
}

/** Feedback tickets with model pre-sorting (kind, module, duplicates) for the weekly triage. */
function FeedbackPage() {
  const feedback = useQuery({ queryKey: ['feedback'], queryFn: api.listFeedback, refetchInterval: 10_000 })
  return (
    <div className="space-y-6">
      <div className="border-b pb-5">
        <p className="page-eyebrow">Wöchentliches Triage-Review</p>
        <h1 className="text-2xl font-semibold tracking-tight">Feedback</h1>
        <p className="mt-1 text-sm text-muted-foreground">Vorsortiert nach Art und Bereich; gleiche Anliegen werden als Duplikat markiert.</p>
      </div>
      <section className="panel" aria-label="Feedback-Tickets">
        {feedback.isPending ? <div className="space-y-3 p-5"><Skeleton className="h-16" /><Skeleton className="h-16" /></div> : null}
        {feedback.isError ? <p role="alert" className="p-5 text-sm text-destructive">{feedback.error.message}</p> : null}
        {feedback.data?.length === 0 ? <p className="p-10 text-center text-sm text-muted-foreground">Noch kein Feedback. Der Button unten rechts erstellt ein Ticket mit Screenshot.</p> : null}
        <ul className="divide-y">{feedback.data?.map((item) => <Entry key={item.id} item={item} all={feedback.data} />)}</ul>
      </section>
    </div>
  )
}
