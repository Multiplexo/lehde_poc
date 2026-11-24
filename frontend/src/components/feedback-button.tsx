import { useId, useState, type FormEvent } from 'react'
import { useMutation } from '@tanstack/react-query'
import { useParams, useRouterState } from '@tanstack/react-router'
import html2canvas from 'html2canvas-pro'
import { Camera, MessageSquarePlus } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { NativeSelect, NativeSelectOption } from '@/components/ui/native-select'
import { Textarea } from '@/components/ui/textarea'
import { api, type FeedbackKind } from '@/lib/api'
import { feedbackKindLabels } from '@/lib/labels'

const NAME_KEY = 'feedback-name'

function storedName(): string {
  try {
    return localStorage.getItem(NAME_KEY) ?? ''
  } catch {
    return ''
  }
}

async function captureScreen(): Promise<string | null> {
  try {
    const canvas = await html2canvas(document.body, {
      scale: Math.min(window.devicePixelRatio, 1.5),
      x: window.scrollX,
      y: window.scrollY,
      width: window.innerWidth,
      height: window.innerHeight,
      logging: false,
      ignoreElements: (element) => element.hasAttribute('data-feedback-ignore'),
    })
    return canvas.toDataURL('image/png')
  } catch {
    return null
  }
}

/** In-app feedback (US-7): creates a ticket with screenshot, URL and text. */
export function FeedbackButton() {
  const id = useId()
  const href = useRouterState({ select: (state) => state.location.href })
  const { projectId } = useParams({ strict: false })
  const [open, setOpen] = useState(false)
  const [capturing, setCapturing] = useState(false)
  const [screenshot, setScreenshot] = useState<string | null>(null)
  const [includeScreenshot, setIncludeScreenshot] = useState(true)
  const [kind, setKind] = useState<FeedbackKind | ''>('')
  const [message, setMessage] = useState('')
  const [name, setName] = useState(storedName)
  const send = useMutation({ mutationFn: api.createFeedback })

  async function start() {
    setCapturing(true)
    setScreenshot(await captureScreen())
    setCapturing(false)
    setOpen(true)
  }

  function close() {
    if (send.isPending) return
    setOpen(false)
    setMessage('')
    setKind('')
    setScreenshot(null)
    setIncludeScreenshot(true)
    send.reset()
  }

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    try {
      localStorage.setItem(NAME_KEY, name.trim())
    } catch {
      // Storage may be blocked; the name is only a convenience.
    }
    send.mutate({
      message: message.trim(),
      kind: kind || null,
      url: window.location.origin + href,
      project_id: projectId ?? null,
      screenshot: includeScreenshot ? screenshot : null,
      user_name: name.trim() || null,
      user_agent: navigator.userAgent.slice(0, 500),
    })
  }

  return <>
    <button type="button" data-feedback-ignore onClick={() => void start()} disabled={capturing}
      className="fixed right-5 bottom-5 z-40 flex items-center gap-2 rounded-full bg-brand px-4 py-2.5 text-sm font-medium text-brand-foreground shadow-lg hover:opacity-90 disabled:opacity-60">
      <MessageSquarePlus aria-hidden="true" className="size-4" />{capturing ? 'Screenshot …' : 'Feedback'}
    </button>
    <Dialog open={open} onOpenChange={(next) => { if (!next) close() }}>
      <DialogContent className="sm:max-w-xl" showCloseButton={!send.isPending}>
        <DialogHeader>
          <DialogTitle>Feedback zum Prototyp</DialogTitle>
          <DialogDescription>Was fehlt, was stimmt nicht, was wäre hilfreich? Screenshot und Seitenadresse werden automatisch angehängt.</DialogDescription>
        </DialogHeader>
        {send.isSuccess ? <>
          <p role="status" className="text-sm text-ok">Danke! Ihr Feedback wurde als Ticket erfasst.</p>
          <DialogFooter><Button onClick={close}>Schließen</Button></DialogFooter>
        </> : (
          <form onSubmit={submit} className="space-y-4">
            <fieldset disabled={send.isPending} className="space-y-4">
              <div className="grid gap-4 sm:grid-cols-2">
                <div className="space-y-1.5">
                  <label htmlFor={`${id}-kind`} className="text-sm font-medium">Art (optional)</label>
                  <NativeSelect id={`${id}-kind`} value={kind} onChange={(event) => setKind(event.target.value as FeedbackKind | '')} className="w-full">
                    <NativeSelectOption value="">Automatisch einordnen</NativeSelectOption>
                    {(Object.keys(feedbackKindLabels) as FeedbackKind[]).map((value) => <NativeSelectOption key={value} value={value}>{feedbackKindLabels[value]}</NativeSelectOption>)}
                  </NativeSelect>
                </div>
                <div className="space-y-1.5">
                  <label htmlFor={`${id}-name`} className="text-sm font-medium">Ihr Name (optional)</label>
                  <Input id={`${id}-name`} value={name} onChange={(event) => setName(event.target.value)} maxLength={200} autoComplete="name" />
                </div>
              </div>
              <div className="space-y-1.5">
                <label htmlFor={`${id}-message`} className="text-sm font-medium">Ihre Nachricht</label>
                <Textarea id={`${id}-message`} value={message} onChange={(event) => setMessage(event.target.value)} required minLength={3} maxLength={4000} rows={5} autoFocus
                  placeholder="z. B. Der Grundwasserstand aus dem Gutachten fehlt, oder: Diese Abweichung ist für uns nicht relevant, weil …" />
              </div>
              {screenshot ? (
                <div className="space-y-2">
                  <label className="flex items-center gap-2 text-sm">
                    <input type="checkbox" checked={includeScreenshot} onChange={(event) => setIncludeScreenshot(event.target.checked)} className="size-4 accent-[var(--brand)]" />
                    <Camera aria-hidden="true" className="size-4 text-muted-foreground" />Screenshot anhängen
                  </label>
                  {includeScreenshot ? <img src={screenshot} alt="Vorschau des Screenshots" className="max-h-40 rounded-md border object-contain" /> : null}
                </div>
              ) : <p className="text-xs text-muted-foreground">Screenshot konnte nicht erstellt werden; das Ticket enthält Text und Seitenadresse.</p>}
            </fieldset>
            {send.error ? <p role="alert" className="text-sm text-destructive">{send.error.message}</p> : null}
            <DialogFooter>
              <Button type="button" variant="outline" onClick={close} disabled={send.isPending}>Abbrechen</Button>
              <Button type="submit" disabled={send.isPending || message.trim().length < 3}>{send.isPending ? 'Wird gesendet …' : 'Feedback senden'}</Button>
            </DialogFooter>
          </form>
        )}
      </DialogContent>
    </Dialog>
  </>
}
