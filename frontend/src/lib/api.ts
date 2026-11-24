// Types mirror the backend Pydantic models (backend/app/models).

export type DocumentType = 'plan' | 'baubeschreibung' | 'brandschutzkonzept' | 'bodengutachten' | 'baugenehmigung' | 'sonstiges'
export type DocumentStatus = 'uploaded' | 'read' | 'classified' | 'failed'
export type ValueSource = 'ai' | 'manual'
export type ProjectStatus = 'draft' | 'processing' | 'ready' | 'failed'
export type AnalysisStep = 'reading' | 'classifying' | 'extracting' | 'comparing' | 'done'
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
}

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
