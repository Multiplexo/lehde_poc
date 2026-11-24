import { Check, Clock } from 'lucide-react'

const included = [
  'Anfragepaket hochladen, auch gescannte PDFs',
  'Dokumenttyp und Planstand je Dokument',
  'Kalkulationsrelevante Fakten mit Fundstelle',
  'Widersprüche zwischen den Unterlagen',
  'Rückfrageliste an Architekt / Bauherr',
  'Projektsteckbrief für die Übergabe',
]
const later = [
  'LV-Entwurf aus Funktionalausschreibung',
  'Prüf-Agenten für VOB und Brandschutznormen',
  'Vertrags-Q&A über das Vertragswerk',
  'Subunternehmer-Vorschläge je Gewerk',
  'Anbindung an Kalkulation, DMS und E-Mail',
]

/** Shows the scope cut in every demo, as agreed in the briefing. */
export function ScopeNote() {
  return (
    <aside className="panel space-y-4 p-5 text-sm" aria-label="Umfang des Prototyps">
      <div>
        <p className="page-eyebrow">Umfang dieses Prototyps</p>
        <ul className="space-y-1.5">
          {included.map((item) => <li key={item} className="flex gap-2"><Check aria-hidden="true" className="mt-0.5 size-4 shrink-0 text-ok" />{item}</li>)}
        </ul>
      </div>
      <div>
        <p className="page-eyebrow">Bewusst später (Stufe 2/3)</p>
        <ul className="space-y-1.5 text-muted-foreground">
          {later.map((item) => <li key={item} className="flex gap-2"><Clock aria-hidden="true" className="mt-0.5 size-4 shrink-0" />{item}</li>)}
        </ul>
      </div>
      <p className="border-t pt-3 text-xs text-muted-foreground">Jede angezeigte Aussage ist mit einem Zitat aus den Unterlagen belegt. Was nicht gefunden wird, steht als „nicht gefunden“ da und wird nie geraten.</p>
    </aside>
  )
}
