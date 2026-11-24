import { useId, useRef, useState, type DragEvent } from 'react'
import { FileUp, FileText, X } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { formatBytes } from '@/lib/labels'
import { cn } from '@/lib/utils'

const ACCEPTED = ['.pdf', '.docx', '.x81', '.x83', '.x84', '.x86', '.xml']

function accepted(file: File): boolean {
  return ACCEPTED.some((suffix) => file.name.toLowerCase().endsWith(suffix))
}

/** Drag & drop file picker for an inquiry package (PDF, DOCX). */
export function UploadDropzone({ files, onChange, disabled, maxFiles }: {
  files: File[]; onChange: (files: File[]) => void; disabled?: boolean; maxFiles: number
}) {
  const id = useId()
  const input = useRef<HTMLInputElement>(null)
  const [dragging, setDragging] = useState(false)
  const [rejected, setRejected] = useState<string[]>([])

  function add(list: FileList | null) {
    if (!list) return
    const incoming = [...list]
    setRejected(incoming.filter((file) => !accepted(file)).map((file) => file.name))
    const known = new Set(files.map((file) => `${file.name}:${file.size}`))
    const next = [...files, ...incoming.filter((file) => accepted(file) && !known.has(`${file.name}:${file.size}`))]
    onChange(next.slice(0, maxFiles))
  }

  function drop(event: DragEvent<HTMLDivElement>) {
    event.preventDefault()
    setDragging(false)
    if (!disabled) add(event.dataTransfer.files)
  }

  return (
    <div className="space-y-3">
      <div onDragOver={(event) => { event.preventDefault(); if (!disabled) setDragging(true) }} onDragLeave={() => setDragging(false)} onDrop={drop}
        className={cn('flex flex-col items-center justify-center gap-2 rounded-xl border-2 border-dashed px-6 py-8 text-center transition-colors',
          dragging ? 'border-brand bg-accent' : 'border-input bg-muted/40', disabled && 'opacity-60')}>
        <FileUp aria-hidden="true" className="size-8 text-muted-foreground" />
        <p className="text-sm font-medium">Unterlagen hierher ziehen</p>
        <p className="text-xs text-muted-foreground">PDF, DOCX oder GAEB (X83/X84), bis zu {maxFiles} Dokumente: Pläne, Baubeschreibung, LV, Vertrag, Gutachten, Baugenehmigung …</p>
        <input ref={input} id={id} type="file" multiple accept={ACCEPTED.join(',')} className="sr-only" disabled={disabled}
          onChange={(event) => { add(event.target.files); event.target.value = '' }} />
        <Button type="button" size="sm" variant="outline" disabled={disabled} onClick={() => input.current?.click()}>Dateien auswählen</Button>
      </div>
      {rejected.length ? <p role="alert" className="text-xs text-destructive">Nicht unterstützt: {rejected.join(', ')}</p> : null}
      {files.length ? (
        <ul className="divide-y rounded-lg border">
          {files.map((file) => (
            <li key={`${file.name}:${file.size}`} className="flex items-center gap-3 px-3 py-2 text-sm">
              <FileText aria-hidden="true" className="size-4 shrink-0 text-muted-foreground" />
              <span className="min-w-0 flex-1 truncate">{file.name}</span>
              <span className="text-xs text-muted-foreground">{formatBytes(file.size)}</span>
              <button type="button" disabled={disabled} onClick={() => onChange(files.filter((item) => item !== file))}
                className="rounded p-1 text-muted-foreground hover:bg-muted hover:text-foreground" aria-label={`${file.name} entfernen`}>
                <X aria-hidden="true" className="size-4" />
              </button>
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  )
}
