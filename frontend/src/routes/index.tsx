import { createFileRoute, Link } from '@tanstack/react-router'
import { AlertTriangle, CircleCheck, FolderOpen, Loader2 } from 'lucide-react'
import { NewPackageDialog } from '@/components/new-package-dialog'
import { ScopeNote } from '@/components/scope-note'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { useProjects } from '@/hooks/use-projects'
import type { ProjectListItem } from '@/lib/api'
import { brand } from '@/lib/brand'
import { formatDate, projectStatusLabels } from '@/lib/labels'

export const Route = createFileRoute('/')({ component: ProjectsPage })

function StatusBadge({ project }: { project: ProjectListItem }) {
  if (project.status === 'processing') return <Badge variant="secondary"><Loader2 aria-hidden="true" className="animate-spin" />{projectStatusLabels.processing}</Badge>
  if (project.status === 'failed') return <Badge variant="destructive">{projectStatusLabels.failed}</Badge>
  if (project.status === 'ready' && project.open_discrepancies === 0) return <Badge variant="outline" className="text-ok"><CircleCheck aria-hidden="true" />Keine offenen Abweichungen</Badge>
  if (project.status === 'ready') {
    return <Badge variant="outline" className={project.red_discrepancies ? 'border-critical/40 text-critical' : 'border-warn/40 text-warn'}>
      <AlertTriangle aria-hidden="true" />{project.open_discrepancies} offene Abweichungen{project.red_discrepancies ? `, ${project.red_discrepancies} kritisch` : ''}
    </Badge>
  }
  return <Badge variant="secondary">{projectStatusLabels[project.status]}</Badge>
}

function ProjectsPage() {
  const projects = useProjects()
  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-4 border-b pb-5">
        <div>
          <p className="page-eyebrow">Kalkulation</p>
          <h1 className="text-2xl font-semibold tracking-tight">Anfragepakete</h1>
          <p className="mt-1 text-sm text-muted-foreground">{brand.tagline}</p>
        </div>
        <NewPackageDialog />
      </div>
      <div className="grid gap-6 lg:grid-cols-[1fr_340px]">
        <section aria-label="Anfragepakete" className="panel divide-y">
          {projects.isPending ? <div className="space-y-3 p-5">{[0, 1, 2].map((key) => <Skeleton key={key} className="h-12" />)}</div> : null}
          {projects.isError ? <p role="alert" className="p-5 text-sm text-destructive">{projects.error.message}</p> : null}
          {projects.data?.length === 0 ? (
            <div className="flex flex-col items-center gap-2 p-10 text-center text-sm text-muted-foreground">
              <FolderOpen aria-hidden="true" className="size-8" />
              <p>Noch keine Anfragepakete. Laden Sie die Unterlagen einer Anfrage hoch, um zu starten.</p>
              <p className="text-xs">Zum Ausprobieren liegt ein fiktives Beispielpaket im Repository unter <code>demo/anfragepaket</code>.</p>
            </div>
          ) : null}
          {projects.data?.map((project) => (
            <Link key={project.id} to="/projekte/$projectId" params={{ projectId: project.id }}
              className="flex flex-wrap items-center gap-x-6 gap-y-2 px-5 py-4 hover:bg-muted/50">
              <div className="min-w-0 flex-1">
                <p className="truncate font-medium">{project.name}</p>
                <p className="text-xs text-muted-foreground">{project.document_count} Dokumente · angelegt {formatDate(project.created_at)}</p>
              </div>
              <StatusBadge project={project} />
            </Link>
          ))}
        </section>
        <ScopeNote />
      </div>
    </div>
  )
}
