import { useState, type FormEvent } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Bot, Eraser, Send, ShieldAlert } from 'lucide-react'
import { SourceChip } from '@/components/source/source-chip'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { api, type ChatMessage, type Project } from '@/lib/api'
import { cn } from '@/lib/utils'

const examples = [
  'Was schulden wir eigentlich?',
  'Welche Vertragsstrafe ist vereinbart?',
  'Wer trägt die Entsorgung belasteter Böden?',
  'Welche Leistungen sind bauseits?',
]

function Message({ message }: { message: ChatMessage }) {
  const user = message.role === 'user'
  return (
    <li className={cn('flex', user ? 'justify-end' : 'justify-start')}>
      <div className={cn('max-w-3xl space-y-2 rounded-xl px-4 py-3 text-sm', user ? 'bg-brand text-brand-foreground' : 'border bg-card')}>
        {message.unsupported ? <p className="flex items-center gap-1.5 text-xs text-warn"><ShieldAlert aria-hidden="true" className="size-3.5" />Ohne belegtes Zitat keine Antwort</p> : null}
        <p className="whitespace-pre-line">{message.content}</p>
        {message.sources.length ? (
          <div className="flex flex-wrap gap-1.5 border-t pt-2">{message.sources.map((source, index) => <SourceChip key={index} source={source} label="Antwort" />)}</div>
        ) : null}
      </div>
    </li>
  )
}

/** Project Supermind: questions about the documents, answers only with quotes. */
export function ChatTab({ project }: { project: Project }) {
  const client = useQueryClient()
  const key = ['chat', project.id]
  const messages = useQuery({ queryKey: key, queryFn: () => api.listChat(project.id) })
  const [question, setQuestion] = useState('')
  const ask = useMutation({
    mutationFn: (text: string) => api.ask(project.id, text),
    onSuccess: (added) => {
      client.setQueryData<ChatMessage[]>(key, (current) => [...(current ?? []), ...added])
      setQuestion('')
    },
  })
  const clear = useMutation({ mutationFn: () => api.clearChat(project.id), onSuccess: () => client.setQueryData(key, []) })

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (question.trim().length >= 3) ask.mutate(question.trim())
  }

  return (
    <div className="mx-auto max-w-4xl space-y-4">
      <div className="flex flex-wrap items-center gap-3">
        <p className="text-sm text-muted-foreground">Fragen an Vertrag, LV und Gutachten dieses Projekts. Jede Antwort nennt ihre Fundstellen; ohne belegtes Zitat gibt es keine Antwort.</p>
        {messages.data?.length ? <Button size="sm" variant="ghost" className="ml-auto" disabled={clear.isPending} onClick={() => clear.mutate()}><Eraser aria-hidden="true" />Verlauf leeren</Button> : null}
      </div>
      <ul className="space-y-3">
        {messages.data?.map((message) => <Message key={message.id} message={message} />)}
        {ask.isPending ? <li className="flex items-center gap-2 text-sm text-muted-foreground" role="status"><Bot aria-hidden="true" className="size-4 animate-pulse" />Suche in den Unterlagen …</li> : null}
      </ul>
      {messages.data?.length === 0 && !ask.isPending ? (
        <div className="flex flex-wrap gap-2">
          {examples.map((example) => <Button key={example} size="sm" variant="outline" onClick={() => ask.mutate(example)}>{example}</Button>)}
        </div>
      ) : null}
      {ask.error ? <p role="alert" className="text-sm text-destructive">{ask.error.message}</p> : null}
      <form onSubmit={submit} className="panel flex items-end gap-2 p-2">
        <Textarea value={question} onChange={(event) => setQuestion(event.target.value)} rows={2} maxLength={2000} aria-label="Frage an die Unterlagen"
          placeholder="z. B. Welche Gewährleistungsfrist gilt?" className="border-0 shadow-none focus-visible:ring-0"
          onKeyDown={(event) => { if (event.key === 'Enter' && !event.shiftKey) { event.preventDefault(); event.currentTarget.form?.requestSubmit() } }} />
        <Button type="submit" disabled={ask.isPending || question.trim().length < 3}><Send aria-hidden="true" />Fragen</Button>
      </form>
    </div>
  )
}
