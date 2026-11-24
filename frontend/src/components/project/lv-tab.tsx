import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Download, FileSpreadsheet, Lightbulb, Mail, Plus, RefreshCw, Sparkles, Trash2, Users } from 'lucide-react'
import { SourceChip } from '@/components/source/source-chip'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { NativeSelect, NativeSelectOption } from '@/components/ui/native-select'
import { Skeleton } from '@/components/ui/skeleton'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { projectKeys } from '@/hooks/use-projects'
import { api, lvExportUrl, requestLetterUrl, type LvPosition, type LvPositionUpdate, type Project, type Trade, type TradeSummary } from '@/lib/api'
import { lvOriginLabels } from '@/lib/labels'
import { cn } from '@/lib/utils'

const LOW_CONFIDENCE = 0.6

function useLv(project: Project) {
  return useQuery({ queryKey: ['lv', project.id, project.updated_at], queryFn: () => api.getLv(project.id) })
}

function useTrades() {
  return useQuery({ queryKey: ['trades'], queryFn: api.listTrades, staleTime: Infinity })
}

function QuantityInput({ position, disabled, onSave }: { position: LvPosition; disabled: boolean; onSave: (value: number | null) => void }) {
  const [draft, setDraft] = useState(position.quantity === null ? '' : String(position.quantity).replace('.', ','))
  function commit() {
    const value = draft.trim() === '' ? null : Number(draft.replace(/\./g, '').replace(',', '.'))
    if (value !== null && Number.isNaN(value)) return
    if (value !== position.quantity) onSave(value)
  }
  return <Input aria-label={`Menge ${position.oz ?? position.short_text}`} value={draft} disabled={disabled} inputMode="decimal"
    className="h-8 w-24 text-right tabular-nums" onChange={(event) => setDraft(event.target.value)} onBlur={commit}
    onKeyDown={(event) => { if (event.key === 'Enter') event.currentTarget.blur() }} />
}

function PositionRow({ position, trades, disabled, onUpdate, onDelete }: {
  position: LvPosition; trades: Trade[]; disabled: boolean
  onUpdate: (data: LvPositionUpdate) => void; onDelete: () => void
}) {
  const uncertain = position.trade_source === 'ai' && position.trade_confidence !== null && position.trade_confidence < LOW_CONFIDENCE
  return (
    <TableRow className={cn('align-top', !position.included && 'opacity-50')}>
      <TableCell className="w-8">
        <input type="checkbox" checked={position.included} disabled={disabled} aria-label="In Anfrage übernehmen"
          onChange={(event) => onUpdate({ included: event.target.checked })} className="mt-2 size-4 accent-[var(--brand)]" />
      </TableCell>
      <TableCell className="font-mono text-xs whitespace-nowrap">{position.oz ?? '–'}</TableCell>
      <TableCell className="min-w-72 max-w-xl">
        <p className="font-medium">{position.short_text}</p>
        {position.long_text ? (
          <details>
            <summary className="cursor-pointer text-xs text-muted-foreground select-none">Langtext</summary>
            <p className="mt-1 text-xs whitespace-pre-line text-muted-foreground">{position.long_text}</p>
          </details>
        ) : null}
        <div className="mt-1 flex flex-wrap items-center gap-1.5">
          <Badge variant="secondary">{lvOriginLabels[position.origin]}</Badge>
          {position.source ? <SourceChip source={position.source} label={position.oz ?? 'LV-Position'} /> : null}
          {position.assumption ? <Badge variant="outline" className="border-warn/40 text-warn" title={position.assumption}><Lightbulb aria-hidden="true" />Annahme</Badge> : null}
          {position.assumption ? <span className="text-xs text-muted-foreground">{position.assumption}</span> : null}
          {position.quantity_formula ? <span className="text-xs text-muted-foreground">Menge = {position.quantity_formula}</span> : null}
        </div>
      </TableCell>
      <TableCell className="text-right"><QuantityInput key={String(position.quantity)} position={position} disabled={disabled} onSave={(quantity) => onUpdate({ quantity })} /></TableCell>
      <TableCell className="text-sm">{position.unit ?? '–'}</TableCell>
      <TableCell className="min-w-56">
        <NativeSelect aria-label="Gewerk" value={position.trade_code ?? ''} disabled={disabled} className="w-full"
          onChange={(event) => onUpdate({ trade_code: event.target.value })}>
          {position.trade_code ? null : <NativeSelectOption value="">nicht zugeordnet</NativeSelectOption>}
          {trades.map((trade) => <NativeSelectOption key={trade.code} value={trade.code}>{trade.code} {trade.label}</NativeSelectOption>)}
        </NativeSelect>
        {position.trade_source === 'manual' ? <Badge variant="outline" className="mt-1">manuell</Badge> : null}
        {uncertain ? <Badge variant="outline" className="mt-1 border-warn/40 text-warn">unsicher</Badge> : null}
      </TableCell>
      <TableCell>
        {position.origin === 'manual' || position.origin === 'draft' ? (
          <Button size="icon-sm" variant="ghost" disabled={disabled} aria-label="Position löschen" onClick={onDelete}><Trash2 aria-hidden="true" /></Button>
        ) : null}
      </TableCell>
    </TableRow>
  )
}

function TradeCard({ projectId, trade, active, onSelect }: { projectId: string; trade: TradeSummary; active: boolean; onSelect: () => void }) {
  return (
    <li className={cn('rounded-lg border bg-card p-3', active && 'border-brand ring-1 ring-brand')}>
      <button type="button" onClick={onSelect} className="flex w-full items-start justify-between gap-2 text-left">
        <span className="min-w-0">
          <span className="block truncate text-sm font-medium">{trade.code} {trade.label}</span>
          <span className="text-xs text-muted-foreground">{trade.position_count} Positionen{trade.assumption_count ? ` · ${trade.assumption_count} Annahmen` : ''}</span>
        </span>
        {trade.own_work ? <Badge className="bg-brand-accent text-brand">Eigenleistung</Badge> : null}
      </button>
      {!trade.own_work ? (
        <div className="mt-2 space-y-1.5 border-t pt-2">
          <div className="flex flex-wrap gap-1.5">
            <Button size="xs" variant="outline" nativeButton={false} render={<a href={lvExportUrl(projectId, trade.code)} download />}><FileSpreadsheet aria-hidden="true" />LV-Auszug</Button>
            <Button size="xs" variant="outline" nativeButton={false} render={<a href={requestLetterUrl(projectId, trade.code)} download />}><Mail aria-hidden="true" />Anschreiben</Button>
          </div>
          {trade.suggestions.length ? (
            <ul className="space-y-1">
              {trade.suggestions.map((sub) => (
                <li key={sub.subcontractor_id} className="flex items-center justify-between gap-2 text-xs">
                  <span className="min-w-0">
                    <span className="block truncate font-medium">{sub.name}</span>
                    <span className="text-muted-foreground">{[sub.postal_code, sub.city].filter(Boolean).join(' ')} · {sub.reason}</span>
                  </span>
                  <a href={requestLetterUrl(projectId, trade.code, sub.subcontractor_id)} download className="shrink-0 underline">Anschreiben</a>
                </li>
              ))}
            </ul>
          ) : <p className="text-xs text-muted-foreground">Keine passenden Subunternehmer in der Liste.</p>}
        </div>
      ) : null}
    </li>
  )
}

/** LV read from GAEB/PDF or drafted from the functional tender, grouped by trade. */
export function LvTab({ project }: { project: Project }) {
  const client = useQueryClient()
  const lv = useLv(project)
  const trades = useTrades()
  const [filter, setFilter] = useState<string | null>(null)
  const [newText, setNewText] = useState('')
  const busy = project.status === 'processing'
  const refresh = () => client.invalidateQueries({ queryKey: ['lv', project.id] })
  const onProject = (updated: Project) => client.setQueryData(projectKeys.detail(project.id), updated)
  const importLv = useMutation({ mutationFn: () => api.importLv(project.id), onSuccess: onProject })
  const draft = useMutation({ mutationFn: () => api.draftLv(project.id), onSuccess: onProject })
  const update = useMutation({
    mutationFn: ({ id, data }: { id: string; data: LvPositionUpdate }) => api.updateLvPosition(project.id, id, data),
    onSuccess: refresh,
  })
  const remove = useMutation({ mutationFn: (id: string) => api.deleteLvPosition(project.id, id), onSuccess: refresh })
  const create = useMutation({
    mutationFn: () => api.createLvPosition(project.id, { short_text: newText.trim(), trade_code: filter }),
    onSuccess: () => { setNewText(''); void refresh() },
  })

  const positions = lv.data?.positions ?? []
  const visible = filter ? positions.filter((item) => (item.trade_code ?? '099') === filter) : positions
  const hasDraft = positions.some((item) => item.origin === 'draft')
  const hasLvDocument = project.documents.some((document) => document.doc_type === 'leistungsverzeichnis')
  const error = importLv.error ?? draft.error ?? update.error ?? remove.error ?? create.error

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-3">
        <p className="max-w-3xl text-sm text-muted-foreground">
          {hasLvDocument ? 'LV aus den Unterlagen eingelesen und Gewerken zugeordnet. ' : 'Im Paket liegt kein LV. '}
          Aus einer Funktionalausschreibung leitet der Entwurf Gewerke und Hauptpositionen ab; Mengen nur, wenn sie aus belegten Maßen berechenbar sind, Annahmen sind markiert.
        </p>
        <div className="ml-auto flex flex-wrap gap-2">
          <Button variant="outline" disabled={busy || importLv.isPending} onClick={() => importLv.mutate()}><RefreshCw aria-hidden="true" />LV neu einlesen</Button>
          <Button disabled={busy || draft.isPending || !project.analysis} onClick={() => {
            if (!hasDraft || window.confirm('Der bestehende LV-Entwurf wird ersetzt. Fortfahren?')) draft.mutate()
          }}><Sparkles aria-hidden="true" />{hasDraft ? 'LV-Entwurf neu ableiten' : 'LV-Entwurf aus Funktionalbeschreibung'}</Button>
          <Button variant="outline" nativeButton={false} render={<a href={lvExportUrl(project.id)} download />}><Download aria-hidden="true" />Excel (alle Gewerke)</Button>
        </div>
      </div>
      {error ? <p role="alert" className="text-sm text-destructive">{error.message}</p> : null}
      {lv.isPending ? <Skeleton className="h-96" /> : null}
      {lv.isError ? <p role="alert" className="text-sm text-destructive">{lv.error.message}</p> : null}
      {lv.data ? (
        <div className="grid gap-4 xl:grid-cols-[340px_1fr]">
          <aside className="space-y-2" aria-label="Gewerke">
            <div className="flex items-center justify-between">
              <h2 className="page-eyebrow mb-0">Gewerke ({lv.data.trades.length})</h2>
              {filter ? <button type="button" className="text-xs underline" onClick={() => setFilter(null)}>alle zeigen</button> : null}
            </div>
            {lv.data.project_postal_code ? <p className="flex items-center gap-1 text-xs text-muted-foreground"><Users aria-hidden="true" className="size-3.5" />Vorschläge nach Region um PLZ {lv.data.project_postal_code}</p> : null}
            <ul className="space-y-2">
              {lv.data.trades.map((trade) => (
                <TradeCard key={trade.code} projectId={project.id} trade={trade} active={filter === trade.code} onSelect={() => setFilter(filter === trade.code ? null : trade.code)} />
              ))}
            </ul>
            {lv.data.trades.length === 0 ? <p className="text-sm text-muted-foreground">Noch keine Positionen.</p> : null}
          </aside>
          <section className="panel min-w-0" aria-label="LV-Positionen">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead><span className="sr-only">In Anfrage</span></TableHead>
                  <TableHead>OZ</TableHead>
                  <TableHead>Position</TableHead>
                  <TableHead className="text-right">Menge</TableHead>
                  <TableHead>Einheit</TableHead>
                  <TableHead>Gewerk</TableHead>
                  <TableHead><span className="sr-only">Aktionen</span></TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {visible.map((position) => (
                  <PositionRow key={position.id} position={position} trades={trades.data ?? []} disabled={busy}
                    onUpdate={(data) => update.mutate({ id: position.id, data })} onDelete={() => remove.mutate(position.id)} />
                ))}
              </TableBody>
            </Table>
            {visible.length === 0 ? <p className="p-6 text-center text-sm text-muted-foreground">Keine Positionen. LV hochladen oder Entwurf ableiten.</p> : null}
            <form className="flex gap-2 border-t p-3" onSubmit={(event) => { event.preventDefault(); if (newText.trim()) create.mutate() }}>
              <Input value={newText} onChange={(event) => setNewText(event.target.value)} placeholder="Eigene Position (Kurztext)" aria-label="Neue Position" disabled={busy} />
              <Button type="submit" variant="outline" disabled={busy || !newText.trim() || create.isPending}><Plus aria-hidden="true" />Hinzufügen</Button>
            </form>
          </section>
        </div>
      ) : null}
    </div>
  )
}
