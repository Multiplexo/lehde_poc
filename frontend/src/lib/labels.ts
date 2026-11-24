import type { AnalysisStep, CheckArea, CheckStatus, DiscrepancyStatus, DocumentType, FeedbackKind, LvOrigin, ProjectStatus, Recipient, Severity } from './api'

export const documentTypeLabels: Record<DocumentType, string> = {
  plan: 'Plan',
  baubeschreibung: 'Baubeschreibung',
  brandschutzkonzept: 'Brandschutzkonzept',
  bodengutachten: 'Bodengutachten',
  baugenehmigung: 'Baugenehmigung',
  leistungsverzeichnis: 'Leistungsverzeichnis',
  vertrag: 'Vertrag / Vertragsentwurf',
  nachtrag: 'Nachtrag',
  sonstiges: 'Sonstiges',
}
export const documentTypes = Object.keys(documentTypeLabels) as DocumentType[]

export const projectStatusLabels: Record<ProjectStatus, string> = {
  draft: 'Entwurf',
  processing: 'Analyse läuft',
  ready: 'Ausgewertet',
  failed: 'Fehler',
}

export const stepLabels: Record<AnalysisStep, string> = {
  reading: 'Dokumente lesen (inkl. OCR)',
  classifying: 'Dokumenttypen und Planstände erkennen',
  extracting: 'Fakten mit Fundstelle extrahieren',
  comparing: 'Unterlagen abgleichen',
  lv: 'LV einlesen, Gewerke zuordnen',
  checking: 'Prüf-Agenten',
  drafting: 'LV-Entwurf ableiten',
  done: 'Fertig',
}
export const analysisSteps: AnalysisStep[] = ['reading', 'classifying', 'extracting', 'comparing', 'lv', 'checking']

export const checkAreaLabels: Record<CheckArea, string> = {
  vertrag: 'Vertrag / VOB',
  brandschutz: 'Brandschutz',
  baugrund: 'Baugrund',
  nachtrag: 'Nachträge',
}
export const checkStatusLabels: Record<CheckStatus, string> = {
  critical: 'Kritisch',
  note: 'Hinweis',
  missing: 'Nicht geregelt',
  ok: 'In Ordnung',
  not_applicable: 'Nicht relevant',
}

export const lvOriginLabels: Record<LvOrigin, string> = {
  gaeb: 'GAEB',
  document: 'aus LV-Dokument',
  draft: 'Entwurf',
  manual: 'manuell',
}

export function formatQuantity(value: number | null): string {
  if (value === null) return '–'
  return new Intl.NumberFormat('de-DE', { maximumFractionDigits: 3 }).format(value)
}

export const recipientLabels: Record<Recipient, string> = {
  architekt: 'Architekt / Planer',
  bauherr: 'Bauherr',
  kalkulation: 'Kalkulation (intern)',
}
export const recipients = Object.keys(recipientLabels) as Recipient[]

export const discrepancyStatusLabels: Record<DiscrepancyStatus, string> = {
  open: 'Offen',
  question: 'Rückfrage stellen',
  reservation: 'Annahme / Vorbehalt im Angebot',
  done: 'Erledigt',
}
export const discrepancyStatuses = Object.keys(discrepancyStatusLabels) as DiscrepancyStatus[]

export const severityLabels: Record<Severity, string> = { red: 'Kritisch', yellow: 'Prüfen' }

export const feedbackKindLabels: Record<FeedbackKind, string> = { bug: 'Fehler', feature: 'Wunsch', question: 'Frage' }

export const moduleLabels: Record<string, string> = {
  upload: 'Upload',
  dokumente: 'Dokumente',
  fakten: 'Fakten',
  abweichungen: 'Abweichungen',
  rueckfragen: 'Rückfragen',
  steckbrief: 'Steckbrief',
  lv: 'LV & Gewerke',
  pruefung: 'Prüfung',
  fragen: 'Fragen an Unterlagen',
  subunternehmer: 'Subunternehmer',
  sonstiges: 'Sonstiges',
}

export function formatDate(value: string): string {
  return new Intl.DateTimeFormat('de-DE', { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(value))
}

export function formatBytes(bytes: number): string {
  if (bytes < 1024 * 1024) return `${Math.max(1, Math.round(bytes / 1024))} KB`
  return `${(bytes / 1024 / 1024).toFixed(1).replace('.', ',')} MB`
}
