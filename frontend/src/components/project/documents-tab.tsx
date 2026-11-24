import { useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { FileText, ScanText, Trash2, Upload } from 'lucide-react'
import { SourceChip } from '@/components/source/source-chip'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { NativeSelect, NativeSelectOption } from '@/components/ui/native-select'
import { Progress } from '@/components/ui/progress'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { UploadDropzone } from '@/components/upload-dropzone'
import { MAX_DOCUMENTS } from '@/components/new-package-dialog'
import { projectKeys, useDeleteDocument, useUpdateDocument } from '@/hooks/use-projects'
import { uploadDocuments, type DocumentSummary, type DocumentType, type DocumentUpdate, type Project } from '@/lib/api'
import { documentTypeLabels, documentTypes, formatBytes } from '@/lib/labels'

const LOW_CONFIDENCE = 0.6

function EditableText({ value, label, disabled, onSave }: { value: string | null; label: string; disabled: boolean; onSave: (value: string) => void }) {
  const [draft, setDraft] = useState(value ?? '')
  function commit() {
    if (draft.trim() !== (value ?? '')) onSave(draft.trim())
  }
  return <Input aria-label={label} value={draft} disabled={disabled} placeholder="–" className="h-8 min-w-24"
    onChange={(event) => setDraft(event.target.value)} onBlur={commit}
    onKeyDown={(event) => { if (event.key === 'Enter') event.currentTarget.blur() }} />
}

function AddDocumentsDialog({ project }: { project: Project }) {
  const client = useQueryClient()
  const [open, setOpen] = useState(false)
  const [files, setFiles] = useState<File[]>([])
  const [progress, setProgress] = useState<number | null>(null)
  const [error, setError] = useState('')
  async function upload() {
    setError('')
    setProgress(0)
    try {
      await uploadDocuments(project.id, files, setProgress)
      await client.invalidateQueries({ queryKey: projectKeys.detail(project.id) })
      setOpen(false)
      setFiles([])
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Upload fehlgeschlagen')
    } finally {
      setProgress(null)
    }
  }
  return <>
    <Button variant="outline" size="sm" disabled={project.status === 'processing'} onClick={() => setOpen(true)}><Upload aria-hidden="true" />Dokumente hinzufügen</Button>
    <Dialog open={open} onOpenChange={(next) => { if (progress === null) setOpen(next) }}>
      <DialogContent className="sm:max-w-2xl" showCloseButton={progress === null}>
        <DialogHeader>
          <DialogTitle>Dokumente hinzufügen</DialogTitle>
          <DialogDescription>Nach dem Hinzufügen die Analyse neu starten, damit die neuen Unterlagen in den Abgleich eingehen.</DialogDescription>
        </DialogHeader>
        <UploadDropzone files={files} onChange={setFiles} disabled={progress !== null} maxFiles={MAX_DOCUMENTS - project.documents.length} />
        {progress !== null ? <Progress value={Math.round(progress * 100)} /> : null}
        {error ? <p role="alert" className="text-sm text-destructive">{error}</p> : null}
        <DialogFooter>
          <Button variant="outline" disabled={progress !== null} onClick={() => setOpen(false)}>Abbrechen</Button>
          <Button disabled={progress !== null || files.length === 0} onClick={() => void upload()}>Hochladen</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  </>
}

function DocumentRow({ project, document }: { project: Project; document: DocumentSummary }) {
  const update = useUpdateDocument(project.id)
  const remove = useDeleteDocument(project.id)
  const busy = project.status === 'processing' || update.isPending
  const save = (data: DocumentUpdate) => update.mutate({ documentId: document.id, data })
  const uncertain = document.classification_confidence !== null && document.classification_confidence < LOW_CONFIDENCE && document.doc_type_source !== 'manual'
  return (
    <TableRow className="align-top">
      <TableCell className="max-w-72">
        <div className="flex items-start gap-2">
          <FileText aria-hidden="true" className="mt-0.5 size-4 shrink-0 text-muted-foreground" />
          <div className="min-w-0">
            <p className="truncate font-medium" title={document.filename}>{document.filename}</p>
            <p className="text-xs text-muted-foreground">
              {document.page_count ? `${document.page_count} Seiten · ` : ''}{formatBytes(document.size_bytes)}
            </p>
            {document.ocr_page_count ? <Badge variant="secondary" className="mt-1"><ScanText aria-hidden="true" />OCR: {document.ocr_page_count} Seiten gescannt</Badge> : null}
          </div>
        </div>
      </TableCell>
      <TableCell>
        <div className="space-y-1">
          <NativeSelect aria-label={`Dokumenttyp von ${document.filename}`} value={document.doc_type ?? ''} disabled={busy}
            onChange={(event) => save({ doc_type: event.target.value as DocumentType })} className="min-w-44">
            {document.doc_type ? null : <NativeSelectOption value="">noch nicht erkannt</NativeSelectOption>}
            {documentTypes.map((type) => <NativeSelectOption key={type} value={type}>{documentTypeLabels[type]}</NativeSelectOption>)}
          </NativeSelect>
          {document.doc_type_source === 'manual' ? <Badge variant="outline">manuell korrigiert</Badge> : null}
          {uncertain ? <Badge variant="outline" className="border-warn/40 text-warn">unsicher – bitte prüfen</Badge> : null}
        </div>
      </TableCell>
      <TableCell><EditableText key={`title-${document.title}`} label={`Titel von ${document.filename}`} value={document.title} disabled={busy} onSave={(title) => save({ title })} /></TableCell>
      <TableCell><EditableText key={`revision-${document.revision}`} label={`Planstand von ${document.filename}`} value={document.revision} disabled={busy} onSave={(revision) => save({ revision })} /></TableCell>
      <TableCell><EditableText key={`date-${document.document_date}`} label={`Datum von ${document.filename}`} value={document.document_date} disabled={busy} onSave={(document_date) => save({ document_date })} /></TableCell>
      <TableCell className="min-w-48">
        {document.plans.length ? (
          <ul className="space-y-1.5">
            {document.plans.map((plan, index) => (
              <li key={`${plan.plan_number}-${index}`} className="space-y-0.5 text-xs">
                <p><span className="font-medium">{plan.plan_number}</span>{plan.revision ? ` · Index ${plan.revision}` : ''}{plan.date ? ` · ${plan.date}` : ''}</p>
                {plan.title ? <p className="text-muted-foreground">{plan.title}</p> : null}
                {plan.source ? <SourceChip source={plan.source} label="Plankopf" /> : null}
              </li>
            ))}
          </ul>
        ) : <span className="text-xs text-muted-foreground">–</span>}
      </TableCell>
      <TableCell className="text-right">
        <Button size="icon-sm" variant="ghost" disabled={busy || remove.isPending} aria-label={`${document.filename} entfernen`}
          onClick={() => { if (window.confirm(`${document.filename} aus dem Paket entfernen?`)) remove.mutate(document.id) }}>
          <Trash2 aria-hidden="true" />
        </Button>
      </TableCell>
    </TableRow>
  )
}

/** US-2: detected document types and plan revisions, both correctable. */
export function DocumentsTab({ project }: { project: Project }) {
  return (
    <section className="panel" aria-label="Dokumente">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b px-5 py-3">
        <p className="text-sm text-muted-foreground">Typ, Titel, Planstand und Datum sind korrigierbar. Korrekturen am Planstand fließen sofort in den Planstand-Abgleich ein.</p>
        <AddDocumentsDialog project={project} />
      </div>
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Datei</TableHead>
            <TableHead>Typ</TableHead>
            <TableHead>Titel</TableHead>
            <TableHead>Planstand / Version</TableHead>
            <TableHead>Datum</TableHead>
            <TableHead>Pläne laut Plankopf</TableHead>
            <TableHead><span className="sr-only">Aktionen</span></TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {project.documents.map((document) => <DocumentRow key={document.id} project={project} document={document} />)}
        </TableBody>
      </Table>
    </section>
  )
}
