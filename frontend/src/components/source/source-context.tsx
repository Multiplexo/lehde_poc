import { createContext, useContext } from 'react'
import type { DocumentSummary, SourceRef } from '@/lib/api'
import { documentTypeLabels } from '@/lib/labels'

export interface SourceSelection { source: SourceRef; label?: string }

export interface SourceContextValue {
  projectId: string
  documents: Map<string, DocumentSummary>
  names: Map<string, string>
  selected: SourceSelection | null
  open: (selection: SourceSelection) => void
  close: () => void
}

export const SourceContext = createContext<SourceContextValue | null>(null)

export function useSources(): SourceContextValue {
  const value = useContext(SourceContext)
  if (!value) throw new Error('useSources must be used inside SourceProvider')
  return value
}

/** Same naming as the backend: the document type, or title/file name if ambiguous. */
export function documentNames(documents: DocumentSummary[]): Map<string, string> {
  const counts = new Map<string, number>()
  for (const document of documents) {
    if (document.doc_type) counts.set(document.doc_type, (counts.get(document.doc_type) ?? 0) + 1)
  }
  return new Map(documents.map((document) => {
    const type = document.doc_type
    const unique = type && type !== 'sonstiges' && type !== 'plan' && counts.get(type) === 1
    return [document.id, unique ? documentTypeLabels[type] : document.title || document.filename]
  }))
}
