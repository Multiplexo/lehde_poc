import { lazy, Suspense, useCallback, useMemo, useState, type ReactNode } from 'react'
import type { DocumentSummary } from '@/lib/api'
import { documentNames, SourceContext, type SourceSelection } from './source-context'

const SourceDrawer = lazy(() => import('./source-drawer'))

export function SourceProvider({ projectId, documents, children }: { projectId: string; documents: DocumentSummary[]; children: ReactNode }) {
  const [selected, setSelected] = useState<SourceSelection | null>(null)
  const open = useCallback((selection: SourceSelection) => setSelected(selection), [])
  const close = useCallback(() => setSelected(null), [])
  const value = useMemo(() => ({
    projectId,
    documents: new Map(documents.map((document) => [document.id, document])),
    names: documentNames(documents),
    selected,
    open,
    close,
  }), [projectId, documents, selected, open, close])
  return (
    <SourceContext.Provider value={value}>
      {children}
      {selected ? <Suspense fallback={null}><SourceDrawer /></Suspense> : null}
    </SourceContext.Provider>
  )
}
