import { createFileRoute, Link, useNavigate } from '@tanstack/react-router'
import { AlertTriangle, ArrowLeft, RefreshCw, Trash2 } from 'lucide-react'
import { AnalysisProgress } from '@/components/project/analysis-progress'
import { DiscrepanciesTab } from '@/components/project/discrepancies-tab'
import { DocumentsTab } from '@/components/project/documents-tab'
import { FactsTab } from '@/components/project/facts-tab'
import { OnepagerTab } from '@/components/project/onepager-tab'
import { QuestionsTab } from '@/components/project/questions-tab'
import { SourceProvider } from '@/components/source/source-provider'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { useDeleteProject, useProject, useStartAnalysis } from '@/hooks/use-projects'
import type { Project } from '@/lib/api'
import { formatDate } from '@/lib/labels'

const tabs = ['abweichungen', 'fakten', 'rueckfragen', 'steckbrief', 'dokumente'] as const
type Tab = (typeof tabs)[number]

export const Route = createFileRoute('/projekte/$projectId')({
  component: ProjectPage,
  validateSearch: (search: Record<string, unknown>): { tab?: Tab } =>
    tabs.includes(search.tab as Tab) ? { tab: search.tab as Tab } : {},
})

function Header({ project }: { project: Project }) {
  const navigate = useNavigate()
  const start = useStartAnalysis(project.id)
  const remove = useDeleteProject()
  const processing = project.status === 'processing'
  const stats = project.analysis?.stats
  return (
    <div className="space-y-3 border-b pb-5">
      <Link to="/" className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"><ArrowLeft aria-hidden="true" className="size-4" />Anfragepakete</Link>
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div className="min-w-0">
          <p className="page-eyebrow">Anfragepaket</p>
          <h1 className="truncate text-2xl font-semibold tracking-tight">{project.name}</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            {project.documents.length} Dokumente
            {stats ? ` · ${stats.pages} Seiten${stats.ocr_pages ? ` (${stats.ocr_pages} per OCR)` : ''} · ausgewertet ${formatDate(project.analysis!.created_at)} in ${Math.round(stats.duration_seconds)} s` : ''}
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" disabled={processing || start.isPending || project.documents.length === 0} onClick={() => start.mutate()}>
            <RefreshCw aria-hidden="true" className={processing ? 'animate-spin' : undefined} />{project.analysis ? 'Neu auswerten' : 'Auswerten'}
          </Button>
          <Button variant="ghost" size="icon" aria-label="Anfragepaket löschen" disabled={processing || remove.isPending}
            onClick={() => {
              if (window.confirm(`„${project.name}“ mit allen Dokumenten löschen?`)) remove.mutate(project.id, { onSuccess: () => void navigate({ to: '/' }) })
            }}>
            <Trash2 aria-hidden="true" />
          </Button>
        </div>
      </div>
      {start.error ? <p role="alert" className="text-sm text-destructive">{start.error.message}</p> : null}
    </div>
  )
}

function ProjectPage() {
  const { projectId } = Route.useParams()
  const { tab = 'abweichungen' } = Route.useSearch()
  const navigate = useNavigate({ from: Route.fullPath })
  const query = useProject(projectId)
  if (query.isPending) return <div className="space-y-4"><Skeleton className="h-20" /><Skeleton className="h-96" /></div>
  if (query.isError) return <p role="alert" className="text-destructive">{query.error.message}</p>
  const project = query.data
  const analysis = project.analysis
  const open = analysis?.discrepancies.filter((item) => item.status !== 'done') ?? []
  const questionCount = project.questions.filter((item) => item.included).length
  const select = (value: Tab) => void navigate({ search: { tab: value }, replace: true })
  return (
    <SourceProvider projectId={project.id} documents={project.documents}>
      <div className="space-y-6">
        <Header project={project} />
        {project.status === 'processing' ? <AnalysisProgress project={project} /> : null}
        {project.status === 'failed' && project.error ? (
          <p role="alert" className="flex gap-2 rounded-lg border border-destructive/30 bg-destructive/5 p-4 text-sm text-destructive">
            <AlertTriangle aria-hidden="true" className="size-4 shrink-0" />{project.error}
          </p>
        ) : null}
        {!analysis ? (
          project.status === 'processing' ? null : <DocumentsTab project={project} />
        ) : (
          <Tabs value={tab} onValueChange={(value) => select(value as Tab)}>
            <TabsList className="h-auto flex-wrap">
              <TabsTrigger value="abweichungen">Abweichungen ({open.length})</TabsTrigger>
              <TabsTrigger value="fakten">Fakten</TabsTrigger>
              <TabsTrigger value="rueckfragen">Rückfragen ({questionCount})</TabsTrigger>
              <TabsTrigger value="steckbrief">Projektsteckbrief</TabsTrigger>
              <TabsTrigger value="dokumente">Dokumente ({project.documents.length})</TabsTrigger>
            </TabsList>
            <TabsContent value="abweichungen" className="pt-4"><DiscrepanciesTab project={project} onShowQuestions={() => select('rueckfragen')} /></TabsContent>
            <TabsContent value="fakten" className="pt-4"><FactsTab analysis={analysis} /></TabsContent>
            <TabsContent value="rueckfragen" className="pt-4"><QuestionsTab project={project} /></TabsContent>
            <TabsContent value="steckbrief" className="pt-4"><OnepagerTab project={project} /></TabsContent>
            <TabsContent value="dokumente" className="pt-4"><DocumentsTab project={project} /></TabsContent>
          </Tabs>
        )}
      </div>
    </SourceProvider>
  )
}
