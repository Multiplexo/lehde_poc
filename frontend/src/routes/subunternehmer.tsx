import { useId, useRef, useState, type FormEvent } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { createFileRoute } from '@tanstack/react-router'
import { Pencil, Plus, Trash2, Upload } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Skeleton } from '@/components/ui/skeleton'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Textarea } from '@/components/ui/textarea'
import { api, type Subcontractor, type SubcontractorData, type Trade } from '@/lib/api'

export const Route = createFileRoute('/subunternehmer')({ component: SubcontractorsPage })

const empty: SubcontractorData = { name: '', trade_codes: [], postal_code: null, city: null, contact: null, email: null, phone: null, note: null }

function SubcontractorDialog({ trades, initial, onClose }: { trades: Trade[]; initial: Subcontractor | null; onClose: () => void }) {
  const id = useId()
  const client = useQueryClient()
  const [data, setData] = useState<SubcontractorData>(initial ?? empty)
  const save = useMutation({
    mutationFn: () => (initial ? api.updateSubcontractor(initial.id, data) : api.createSubcontractor(data)),
    onSuccess: () => { void client.invalidateQueries({ queryKey: ['subcontractors'] }); onClose() },
  })
  const field = (name: keyof SubcontractorData) => ({
    id: `${id}-${name}`,
    value: (data[name] as string | null) ?? '',
    onChange: (event: { target: { value: string } }) => setData({ ...data, [name]: event.target.value || null }),
  })
  function toggle(code: string) {
    setData({ ...data, trade_codes: data.trade_codes.includes(code) ? data.trade_codes.filter((item) => item !== code) : [...data.trade_codes, code] })
  }
  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    save.mutate()
  }
  return (
    <Dialog open onOpenChange={(open) => { if (!open && !save.isPending) onClose() }}>
      <DialogContent className="sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle>{initial ? 'Subunternehmer bearbeiten' : 'Subunternehmer anlegen'}</DialogTitle>
          <DialogDescription>Gewerke und PLZ steuern die Vorschläge je Gewerk im LV.</DialogDescription>
        </DialogHeader>
        <form onSubmit={submit} className="space-y-4">
          <div className="grid gap-3 sm:grid-cols-2">
            <label className="space-y-1 text-sm font-medium sm:col-span-2" htmlFor={`${id}-name`}>Firma
              <Input {...field('name')} value={data.name} required minLength={2} onChange={(event) => setData({ ...data, name: event.target.value })} />
            </label>
            <label className="space-y-1 text-sm font-medium" htmlFor={`${id}-postal_code`}>PLZ<Input {...field('postal_code')} inputMode="numeric" maxLength={10} /></label>
            <label className="space-y-1 text-sm font-medium" htmlFor={`${id}-city`}>Ort<Input {...field('city')} /></label>
            <label className="space-y-1 text-sm font-medium" htmlFor={`${id}-contact`}>Ansprechpartner<Input {...field('contact')} /></label>
            <label className="space-y-1 text-sm font-medium" htmlFor={`${id}-email`}>E-Mail<Input {...field('email')} type="email" /></label>
            <label className="space-y-1 text-sm font-medium" htmlFor={`${id}-phone`}>Telefon<Input {...field('phone')} type="tel" /></label>
          </div>
          <fieldset className="space-y-2">
            <legend className="text-sm font-medium">Gewerke</legend>
            <div className="grid max-h-56 gap-1 overflow-y-auto rounded-md border p-2 sm:grid-cols-2">
              {trades.filter((trade) => !trade.own_work).map((trade) => (
                <label key={trade.code} className="flex items-center gap-2 text-sm">
                  <input type="checkbox" checked={data.trade_codes.includes(trade.code)} onChange={() => toggle(trade.code)} className="size-4 accent-[var(--brand)]" />
                  {trade.code} {trade.label}
                </label>
              ))}
            </div>
          </fieldset>
          <label className="block space-y-1 text-sm font-medium" htmlFor={`${id}-note`}>Notiz<Textarea {...field('note')} rows={2} /></label>
          {save.error ? <p role="alert" className="text-sm text-destructive">{save.error.message}</p> : null}
          <DialogFooter>
            <Button type="button" variant="outline" onClick={onClose} disabled={save.isPending}>Abbrechen</Button>
            <Button type="submit" disabled={save.isPending || data.name.trim().length < 2}>Speichern</Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}

/** Subcontractor list per trade and region; the customer has no central list yet. */
function SubcontractorsPage() {
  const client = useQueryClient()
  const input = useRef<HTMLInputElement>(null)
  const list = useQuery({ queryKey: ['subcontractors'], queryFn: api.listSubcontractors })
  const trades = useQuery({ queryKey: ['trades'], queryFn: api.listTrades, staleTime: Infinity })
  const [editing, setEditing] = useState<Subcontractor | null | undefined>(undefined)
  const remove = useMutation({ mutationFn: api.deleteSubcontractor, onSuccess: () => client.invalidateQueries({ queryKey: ['subcontractors'] }) })
  const upload = useMutation({ mutationFn: api.importSubcontractors, onSuccess: () => client.invalidateQueries({ queryKey: ['subcontractors'] }) })
  const labels = new Map((trades.data ?? []).map((trade) => [trade.code, trade.label]))
  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-4 border-b pb-5">
        <div>
          <p className="page-eyebrow">Bauleitung · Einkauf</p>
          <h1 className="text-2xl font-semibold tracking-tight">Subunternehmer</h1>
          <p className="mt-1 text-sm text-muted-foreground">Zentrale Liste je Gewerk und Region. CSV-Import mit Spalten name; gewerke; plz; ort; ansprechpartner; email; telefon.</p>
        </div>
        <div className="flex gap-2">
          <input ref={input} type="file" accept=".csv,text/csv" className="sr-only" onChange={(event) => { const file = event.target.files?.[0]; if (file) upload.mutate(file); event.target.value = '' }} />
          <Button variant="outline" disabled={upload.isPending} onClick={() => input.current?.click()}><Upload aria-hidden="true" />CSV importieren</Button>
          <Button onClick={() => setEditing(null)}><Plus aria-hidden="true" />Subunternehmer anlegen</Button>
        </div>
      </div>
      {upload.data ? <p role="status" className="text-sm text-ok">{upload.data.created} importiert{upload.data.skipped.length ? `, übersprungen: ${upload.data.skipped.join(', ')}` : ''}.</p> : null}
      {upload.error ? <p role="alert" className="text-sm text-destructive">{upload.error.message}</p> : null}
      <section className="panel" aria-label="Subunternehmer">
        {list.isPending ? <div className="p-5"><Skeleton className="h-32" /></div> : null}
        {list.isError ? <p role="alert" className="p-5 text-sm text-destructive">{list.error.message}</p> : null}
        {list.data?.length === 0 ? <p className="p-10 text-center text-sm text-muted-foreground">Noch keine Subunternehmer. Legen Sie welche an oder importieren Sie eine CSV-Liste.</p> : null}
        {list.data?.length ? (
          <Table>
            <TableHeader>
              <TableRow><TableHead>Firma</TableHead><TableHead>Gewerke</TableHead><TableHead>Ort</TableHead><TableHead>Kontakt</TableHead><TableHead><span className="sr-only">Aktionen</span></TableHead></TableRow>
            </TableHeader>
            <TableBody>
              {list.data.map((item) => (
                <TableRow key={item.id} className="align-top">
                  <TableCell className="font-medium">{item.name}{item.note ? <p className="text-xs font-normal text-muted-foreground">{item.note}</p> : null}</TableCell>
                  <TableCell><div className="flex max-w-md flex-wrap gap-1">{item.trade_codes.map((code) => <Badge key={code} variant="secondary">{code} {labels.get(code)}</Badge>)}</div></TableCell>
                  <TableCell>{[item.postal_code, item.city].filter(Boolean).join(' ') || '–'}</TableCell>
                  <TableCell className="text-sm">{[item.contact, item.email, item.phone].filter(Boolean).join(' · ') || '–'}</TableCell>
                  <TableCell className="text-right whitespace-nowrap">
                    <Button size="icon-sm" variant="ghost" aria-label={`${item.name} bearbeiten`} onClick={() => setEditing(item)}><Pencil aria-hidden="true" /></Button>
                    <Button size="icon-sm" variant="ghost" aria-label={`${item.name} löschen`} disabled={remove.isPending}
                      onClick={() => { if (window.confirm(`${item.name} löschen?`)) remove.mutate(item.id) }}><Trash2 aria-hidden="true" /></Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        ) : null}
      </section>
      {editing !== undefined && trades.data ? <SubcontractorDialog trades={trades.data} initial={editing} onClose={() => setEditing(undefined)} /> : null}
    </div>
  )
}
