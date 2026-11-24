import { useId, useState, type FormEvent } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { useNavigate } from '@tanstack/react-router'
import { Plus } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Progress } from '@/components/ui/progress'
import { UploadDropzone } from '@/components/upload-dropzone'
import { projectKeys } from '@/hooks/use-projects'
import { api, uploadDocuments } from '@/lib/api'

export const MAX_DOCUMENTS = 20

/** US-1: create a project, upload the package and start the analysis. */
export function NewPackageDialog() {
  const id = useId()
  const navigate = useNavigate()
  const client = useQueryClient()
  const [open, setOpen] = useState(false)
  const [name, setName] = useState('')
  const [files, setFiles] = useState<File[]>([])
  const [progress, setProgress] = useState<number | null>(null)
  const [error, setError] = useState('')
  const busy = progress !== null

  function close(next: boolean) {
    if (busy) return
    setOpen(next)
    if (!next) { setName(''); setFiles([]); setError('') }
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError('')
    setProgress(0)
    try {
      const project = await api.createProject(name.trim())
      await uploadDocuments(project.id, files, setProgress)
      await api.startAnalysis(project.id)
      await client.invalidateQueries({ queryKey: projectKeys.all })
      setProgress(null)
      setOpen(false)
      setName('')
      setFiles([])
      await navigate({ to: '/projekte/$projectId', params: { projectId: project.id } })
    } catch (caught) {
      setProgress(null)
      setError(caught instanceof Error ? caught.message : 'Upload fehlgeschlagen')
    }
  }

  return <>
    <Button onClick={() => setOpen(true)}><Plus aria-hidden="true" />Neues Anfragepaket</Button>
    <Dialog open={open} onOpenChange={close}>
      <DialogContent className="sm:max-w-2xl" showCloseButton={!busy}>
        <DialogHeader>
          <DialogTitle>Neues Anfragepaket</DialogTitle>
          <DialogDescription>Laden Sie alle Unterlagen einer Anfrage hoch. Die Auswertung startet danach automatisch und dauert wenige Minuten.</DialogDescription>
        </DialogHeader>
        <form onSubmit={(event) => void submit(event)} className="space-y-4">
          <div className="space-y-1.5">
            <label htmlFor={`${id}-name`} className="text-sm font-medium">Projektname</label>
            <Input id={`${id}-name`} value={name} onChange={(event) => setName(event.target.value)} required minLength={2} maxLength={200}
              placeholder="z. B. Logistikhalle Gewerbepark Nord" disabled={busy} autoFocus />
          </div>
          <UploadDropzone files={files} onChange={setFiles} disabled={busy} maxFiles={MAX_DOCUMENTS} />
          {busy ? (
            <div className="space-y-1.5" role="status">
              <p className="text-sm">{progress < 1 ? `Hochladen … ${Math.round(progress * 100)} %` : 'Analyse wird gestartet …'}</p>
              <Progress value={Math.round(progress * 100)} />
            </div>
          ) : null}
          {error ? <p role="alert" className="text-sm text-destructive">{error}</p> : null}
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => close(false)} disabled={busy}>Abbrechen</Button>
            <Button type="submit" disabled={busy || files.length === 0 || name.trim().length < 2}>Hochladen und auswerten</Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  </>
}
