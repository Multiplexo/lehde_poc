// Types mirror the backend Pydantic models (backend/app/models).

export type DocumentType = 'plan' | 'baubeschreibung' | 'brandschutzkonzept' | 'bodengutachten' | 'baugenehmigung' | 'leistungsverzeichnis' | 'vertrag' | 'nachtrag' | 'sonstiges'
export type DocumentStatus = 'uploaded' | 'read' | 'classified' | 'failed'
export type ValueSource = 'ai' | 'manual'
export type ProjectStatus = 'draft' | 'processing' | 'ready' | 'failed'
export type AnalysisStep = 'reading' | 'classifying' | 'extracting' | 'comparing' | 'lv' | 'checking' | 'drafting' | 'done'
export type FactStatus = 'found' | 'conflict' | 'not_found'
export type Severity = 'red' | 'yellow'
export type Recipient = 'architekt' | 'bauherr' | 'kalkulation'
export type DiscrepancyStatus = 'open' | 'question' | 'reservation' | 'done'
export type FeedbackKind = 'bug' | 'feature' | 'question'

export interface Box { x: number; y: number; width: number; height: number }
export interface PageLine { text: string; box: Box | null }
export interface PageText { number: number; width: number; height: number; ocr: boolean; lines: PageLine[] }
export interface SourceRef { document_id: string; page: number; quote: string; boxes: Box[]; verified: boolean }

export interface PlanEntry {
  plan_number: string; title: string | null; revision: string | null; date: string | null; document_id: string; source: SourceRef | null
}

export interface DocumentSummary {
  id: string; project_id: string; filename: string; content_type: string; size_bytes: number; created_at: string
  status: DocumentStatus; error: string | null; page_count: number; ocr_page_count: number
  doc_type: DocumentType | null; doc_type_source: ValueSource | null; title: string | null; revision: string | null
  document_date: string | null; meta_source: ValueSource | null; classification_confidence: number | null; plans: PlanEntry[]
}

export interface Claim { id: string; document_id: string; topic: string; value: string; source: SourceRef }
export interface PlanReference { id: string; document_id: string; plan_number: string; revision: string | null; date: string | null; source: SourceRef }
export interface Fact { key: string; label: string; group: string; status: FactStatus; value: string | null; claims: Claim[] }
export interface DiscrepancySide { document_id: string; value: string; source: SourceRef | null }
export interface Discrepancy {
  id: string; kind: 'planstand' | 'content'; topic: string; title: string; explanation: string; severity: Severity
  side_a: DiscrepancySide; side_b: DiscrepancySide | null; recipient: Recipient; question: string; status: DiscrepancyStatus; note: string | null
}
export interface Question {
  id: string; text: string; recipient: Recipient; included: boolean; discrepancy_id: string | null; fact_key: string | null; sources: SourceRef[]
}
export interface AnalysisStats {
  documents: number; pages: number; ocr_pages: number; claims_found: number; claims_dropped: number
  model_calls: number; input_tokens: number; output_tokens: number; duration_seconds: number
}
export interface ProjectAnalysis {
  created_at: string; model: string; summary: { text: string; claim_ids: string[] } | null; facts: Fact[]; claims: Claim[]
  plan_references: PlanReference[]; plan_register: PlanEntry[]; discrepancies: Discrepancy[]; stats: AnalysisStats
}
export interface Project {
  id: string; name: string; created_at: string; updated_at: string; status: ProjectStatus
  progress: { step: AnalysisStep | null; percent: number; message: string | null }; error: string | null
  documents: DocumentSummary[]; analysis: ProjectAnalysis | null; questions: Question[]
  checks: CheckFinding[]; checks_at: string | null
}
export interface ProjectListItem {
  id: string; name: string; created_at: string; updated_at: string; status: ProjectStatus
  document_count: number; open_discrepancies: number; red_discrepancies: number
}
export interface Onepager {
  project_name: string; generated_at: string; summary: string | null
  sections: { label: string; value: string; sources: string[] }[]; open_points: string[]
  documents: { filename: string; doc_type: string; revision: string | null; document_date: string | null }[]
}
export interface Feedback {
  id: string; created_at: string; message: string; kind: FeedbackKind | null; url: string; project_id: string | null
  user_name: string | null; has_screenshot: boolean; forwarded_at: string | null
  triage: { kind: FeedbackKind; module: string; summary: string; duplicate_of: string | null } | null
}
export interface FeedbackCreate {
  message: string; kind: FeedbackKind | null; url: string; project_id: string | null; screenshot: string | null; user_name: string | null; user_agent: string | null
}
export interface DocumentUpdate { doc_type?: DocumentType; title?: string | null; revision?: string | null; document_date?: string | null }
export interface DiscrepancyUpdate { status?: DiscrepancyStatus; recipient?: Recipient; question?: string; note?: string | null }

export type CheckArea = 'vertrag' | 'brandschutz' | 'baugrund' | 'nachtrag'
export type CheckStatus = 'ok' | 'note' | 'critical' | 'missing' | 'not_applicable'
export interface CheckFinding {
  rule_id: string; area: CheckArea; title: string; status: CheckStatus; finding: string; sources: SourceRef[]
  recipient: Recipient; action: string; question: string | null
}

export type LvOrigin = 'gaeb' | 'document' | 'draft' | 'manual'
export interface LvPosition {
  id: string; project_id: string; origin: LvOrigin; sort_index: number; oz: string | null; short_text: string; long_text: string | null
  quantity: number | null; unit: string | null; quantity_formula: string | null; trade_code: string | null; trade_source: ValueSource | null
  trade_confidence: number | null; source: SourceRef | null; assumption: string | null; included: boolean
}
export interface LvPositionUpdate {
  oz?: string | null; short_text?: string; long_text?: string | null; quantity?: number | null; unit?: string | null; trade_code?: string | null; included?: boolean
}
export interface SubcontractorSuggestion { subcontractor_id: string; name: string; city: string | null; postal_code: string | null; email: string | null; reason: string }
export interface TradeSummary {
  code: string; label: string; own_work: boolean; position_count: number; draft_count: number; assumption_count: number; suggestions: SubcontractorSuggestion[]
}
export interface LvOverview { positions: LvPosition[]; trades: TradeSummary[]; project_postal_code: string | null }
export interface Trade { code: string; label: string; hint: string; own_work: boolean }

export interface ChatMessage { id: string; project_id: string; created_at: string; role: 'user' | 'assistant'; content: string; sources: SourceRef[]; unsupported: boolean }

export interface SubcontractorData {
  name: string; trade_codes: string[]; postal_code: string | null; city: string | null; contact: string | null; email: string | null; phone: string | null; note: string | null
}
export interface Subcontractor extends SubcontractorData { id: string; created_at: string }

export const API_BASE = '/api'

export class ApiError extends Error {
  status: number
  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

async function errorMessage(response: Response): Promise<string> {
  try {
    const body = await response.json() as { detail?: unknown }
    if (typeof body.detail === 'string') return body.detail
    if (Array.isArray(body.detail)) return 'Eingabe ungültig. Bitte Werte prüfen.'
  } catch {
    // Body is not JSON; fall through to the status text.
  }
  return `Anfrage fehlgeschlagen (HTTP ${response.status})`
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(API_BASE + path, {
    ...init,
    headers: init?.body && !(init.body instanceof FormData) ? { 'Content-Type': 'application/json', ...init.headers } : init?.headers,
  })
  if (!response.ok) throw new ApiError(response.status, await errorMessage(response))
  if (response.status === 204) return undefined as T
  return await response.json() as T
}

const json = (method: string, body: unknown): RequestInit => ({ method, body: JSON.stringify(body) })

export const api = {
  listProjects: () => request<ProjectListItem[]>('/projects'),
  getProject: (id: string) => request<Project>(`/projects/${id}`),
  createProject: (name: string) => request<Project>('/projects', json('POST', { name })),
  renameProject: (id: string, name: string) => request<Project>(`/projects/${id}`, json('PATCH', { name })),
  deleteProject: (id: string) => request<void>(`/projects/${id}`, { method: 'DELETE' }),
  deleteDocument: (projectId: string, documentId: string) => request<void>(`/projects/${projectId}/documents/${documentId}`, { method: 'DELETE' }),
  updateDocument: (projectId: string, documentId: string, data: DocumentUpdate) =>
    request<Project>(`/projects/${projectId}/documents/${documentId}`, json('PATCH', data)),
  getPages: (projectId: string, documentId: string) =>
    request<{ document_id: string; pages: PageText[] }>(`/projects/${projectId}/documents/${documentId}/pages`),
  startAnalysis: (id: string) => request<Project>(`/projects/${id}/analyze`, { method: 'POST' }),
  updateDiscrepancy: (projectId: string, discrepancyId: string, data: DiscrepancyUpdate) =>
    request<Project>(`/projects/${projectId}/discrepancies/${discrepancyId}`, json('PATCH', data)),
  updateQuestions: (projectId: string, questions: Question[]) => request<Project>(`/projects/${projectId}/questions`, json('PUT', { questions })),
  getOnepager: (projectId: string) => request<Onepager>(`/projects/${projectId}/onepager`),
  listFeedback: () => request<Feedback[]>('/feedback'),
  createFeedback: (data: FeedbackCreate) => request<Feedback>('/feedback', json('POST', data)),
  getLv: (projectId: string) => request<LvOverview>(`/projects/${projectId}/lv`),
  importLv: (projectId: string) => request<Project>(`/projects/${projectId}/lv/import`, { method: 'POST' }),
  draftLv: (projectId: string) => request<Project>(`/projects/${projectId}/lv/draft`, { method: 'POST' }),
  createLvPosition: (projectId: string, data: LvPositionUpdate & { short_text: string }) =>
    request<LvPosition>(`/projects/${projectId}/lv/positions`, json('POST', data)),
  updateLvPosition: (projectId: string, positionId: string, data: LvPositionUpdate) =>
    request<LvPosition>(`/projects/${projectId}/lv/positions/${positionId}`, json('PATCH', data)),
  deleteLvPosition: (projectId: string, positionId: string) => request<void>(`/projects/${projectId}/lv/positions/${positionId}`, { method: 'DELETE' }),
  listTrades: () => request<Trade[]>('/trades'),
  runChecks: (projectId: string) => request<Project>(`/projects/${projectId}/checks`, { method: 'POST' }),
  listChat: (projectId: string) => request<ChatMessage[]>(`/projects/${projectId}/chat`),
  ask: (projectId: string, question: string) => request<ChatMessage[]>(`/projects/${projectId}/chat`, json('POST', { question })),
  clearChat: (projectId: string) => request<void>(`/projects/${projectId}/chat`, { method: 'DELETE' }),
  listSubcontractors: () => request<Subcontractor[]>('/subcontractors'),
  createSubcontractor: (data: SubcontractorData) => request<Subcontractor>('/subcontractors', json('POST', data)),
  updateSubcontractor: (id: string, data: SubcontractorData) => request<Subcontractor>(`/subcontractors/${id}`, json('PUT', data)),
  deleteSubcontractor: (id: string) => request<void>(`/subcontractors/${id}`, { method: 'DELETE' }),
  importSubcontractors: (file: File) => {
    const form = new FormData()
    form.append('file', file)
    return request<{ created: number; skipped: string[] }>('/subcontractors/import', { method: 'POST', body: form })
  },
}

export const lvExportUrl = (projectId: string, trade?: string) =>
  `${API_BASE}/projects/${projectId}/lv/export.xlsx${trade ? `?trade=${encodeURIComponent(trade)}` : ''}`
export const requestLetterUrl = (projectId: string, trade: string, subcontractorId?: string) =>
  `${API_BASE}/projects/${projectId}/lv/requests/${encodeURIComponent(trade)}.docx${subcontractorId ? `?subcontractor_id=${subcontractorId}` : ''}`

export const documentFileUrl = (projectId: string, documentId: string) => `${API_BASE}/projects/${projectId}/documents/${documentId}/file`
export const exportUrl = (projectId: string, file: 'onepager.pdf' | 'onepager.docx' | 'questions.docx' | 'questions.txt') =>
  `${API_BASE}/projects/${projectId}/exports/${file}`
export const screenshotUrl = (feedbackId: string) => `${API_BASE}/feedback/${feedbackId}/screenshot`

/** Upload with progress events; fetch cannot report upload progress. */
export function uploadDocuments(projectId: string, files: File[], onProgress: (fraction: number) => void): Promise<DocumentSummary[]> {
  return new Promise((resolve, reject) => {
    const form = new FormData()
    for (const file of files) form.append('files', file)
    const xhr = new XMLHttpRequest()
    xhr.open('POST', `${API_BASE}/projects/${projectId}/documents`)
    xhr.upload.onprogress = (event) => { if (event.lengthComputable) onProgress(event.loaded / event.total) }
    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        resolve(JSON.parse(xhr.responseText) as DocumentSummary[])
        return
      }
      let message = `Upload fehlgeschlagen (HTTP ${xhr.status})`
      try {
        const body = JSON.parse(xhr.responseText) as { detail?: unknown }
        if (typeof body.detail === 'string') message = body.detail
      } catch {
        // Keep the generic message.
      }
      reject(new ApiError(xhr.status, message))
    }
    xhr.onerror = () => reject(new ApiError(0, 'Upload fehlgeschlagen: Server nicht erreichbar'))
    xhr.send(form)
  })
}
