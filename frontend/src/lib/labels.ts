import type { AnalysisStep, DiscrepancyStatus, DocumentType, FeedbackKind, ProjectStatus, Recipient, Severity } from './api'

export const documentTypeLabels: Record<DocumentType, string> = {
  plan: 'Plan',
  baubeschreibung: 'Baubeschreibung',
  brandschutzkonzept: 'Brandschutzkonzept',
  bodengutachten: 'Bodengutachten',
  baugenehmigung: 'Baugenehmigung',
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
  done: 'Fertig',
}
export const analysisSteps: AnalysisStep[] = ['reading', 'classifying', 'extracting', 'comparing']

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
  sonstiges: 'Sonstiges',
}

export function formatDate(value: string): string {
  return new Intl.DateTimeFormat('de-DE', { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(value))
}

export function formatBytes(bytes: number): string {
  if (bytes < 1024 * 1024) return `${Math.max(1, Math.round(bytes / 1024))} KB`
  return `${(bytes / 1024 / 1024).toFixed(1).replace('.', ',')} MB`
}
