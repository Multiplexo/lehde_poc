import { useState } from 'react'
import { Download, Plus, Trash2 } from 'lucide-react'
import { SourceChip } from '@/components/source/source-chip'
import { Button } from '@/components/ui/button'
import { NativeSelect, NativeSelectOption } from '@/components/ui/native-select'
import { Textarea } from '@/components/ui/textarea'
import { useUpdateQuestions } from '@/hooks/use-projects'
import { exportUrl, type Project, type Question, type Recipient } from '@/lib/api'
import { recipientLabels, recipients } from '@/lib/labels'

/** US-5: numbered questions to architect / client with source, exported as DOCX or text. */
export function QuestionsTab({ project }: { project: Project }) {
  const save = useUpdateQuestions(project.id)
  // Local edits; null means the list shows the saved state from the server.
  const [edits, setEdits] = useState<Question[] | null>(null)
  const draft = edits ?? project.questions
  const dirty = edits !== null

  function edit(update: (items: Question[]) => Question[]) {
    setEdits(update(draft))
  }

  function change(id: string, patch: Partial<Question>) {
    edit((items) => items.map((item) => (item.id === id ? { ...item, ...patch } : item)))
  }

  function add() {
    edit((items) => [...items, { id: `q-own-${crypto.randomUUID()}`, text: '', recipient: 'architekt', included: true, discrepancy_id: null, fact_key: null, sources: [] }])
  }

  function persist() {
    const cleaned = draft.filter((item) => item.text.trim().length > 0).map((item) => ({ ...item, text: item.text.trim() }))
    save.mutate(cleaned, { onSuccess: () => setEdits(null) })
  }

  const included = draft.filter((item) => item.included)
  // Numbering follows the export: grouped by recipient, only included questions.
  const numbers = new Map(
    recipients.flatMap((recipient) => included.filter((item) => item.recipient === recipient)).map((item, index) => [item.id, index + 1]),
  )
  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-3">
        <p className="text-sm text-muted-foreground">{included.length} von {draft.length} Fragen im Export. Texte sind frei bearbeitbar; Quellenangaben werden mit exportiert.</p>
        <div className="ml-auto flex flex-wrap gap-2">
          <Button variant="outline" onClick={add}><Plus aria-hidden="true" />Eigene Frage</Button>
          <Button onClick={persist} disabled={!dirty || save.isPending}>{save.isPending ? 'Speichern …' : 'Speichern'}</Button>
          <Button variant="outline" disabled={dirty} nativeButton={false} render={<a href={exportUrl(project.id, 'questions.docx')} download />}><Download aria-hidden="true" />DOCX</Button>
          <Button variant="outline" disabled={dirty} nativeButton={false} render={<a href={exportUrl(project.id, 'questions.txt')} download />}><Download aria-hidden="true" />Text</Button>
        </div>
      </div>
      {dirty ? <p role="status" className="text-xs text-warn">Ungespeicherte Änderungen – vor dem Export speichern.</p> : null}
      {save.error ? <p role="alert" className="text-sm text-destructive">{save.error.message}</p> : null}
      {recipients.map((recipient: Recipient) => {
        const items = draft.filter((item) => item.recipient === recipient)
        if (!items.length) return null
        return (
          <section key={recipient} className="panel" aria-label={recipientLabels[recipient]}>
            <h2 className="border-b px-5 py-3 font-medium">An: {recipientLabels[recipient]}</h2>
            <ol className="divide-y">
              {items.map((item) => {
                const number = numbers.get(item.id)
                return (
                  <li key={item.id} className="flex gap-3 px-5 py-3">
                    <div className="flex w-14 shrink-0 flex-col items-start gap-2 pt-1">
                      <span className="text-sm font-semibold tabular-nums">{number ? `${number}.` : '–'}</span>
                      <label className="flex items-center gap-1 text-xs text-muted-foreground">
                        <input type="checkbox" checked={item.included} onChange={(event) => change(item.id, { included: event.target.checked })} className="size-4 accent-[var(--brand)]" />
                        Export
                      </label>
                    </div>
                    <div className="min-w-0 flex-1 space-y-2">
                      <Textarea aria-label="Fragetext" value={item.text} rows={2} onChange={(event) => change(item.id, { text: event.target.value })} />
                      <div className="flex flex-wrap items-center gap-2">
                        <NativeSelect aria-label="Empfänger" value={item.recipient} onChange={(event) => change(item.id, { recipient: event.target.value as Recipient })}>
                          {recipients.map((value) => <NativeSelectOption key={value} value={value}>{recipientLabels[value]}</NativeSelectOption>)}
                        </NativeSelect>
                        {item.sources.map((source, index) => <SourceChip key={index} source={source} />)}
                        {item.fact_key ? <span className="text-xs text-muted-foreground">fehlende Angabe</span> : null}
                        {item.id.startsWith('q-own-') ? (
                          <Button size="icon-sm" variant="ghost" aria-label="Frage löschen" onClick={() => edit((list) => list.filter((entry) => entry.id !== item.id))}>
                            <Trash2 aria-hidden="true" />
                          </Button>
                        ) : null}
                      </div>
                    </div>
                  </li>
                )
              })}
            </ol>
          </section>
        )
      })}
    </div>
  )
}
