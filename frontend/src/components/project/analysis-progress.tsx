import { Check, Loader2 } from 'lucide-react'
import { Progress } from '@/components/ui/progress'
import type { Project } from '@/lib/api'
import { analysisSteps, stepLabels } from '@/lib/labels'
import { cn } from '@/lib/utils'

export function AnalysisProgress({ project }: { project: Project }) {
  const current = project.progress.step ? analysisSteps.indexOf(project.progress.step) : 0
  // Separate jobs (LV draft, LV import, re-checks) run at 30 % and show only
  // the message; in the full analysis the LV and check steps start at 78 %.
  const step = project.progress.step
  const fullRun = step === null || step === 'done' ? true
    : ['reading', 'classifying', 'extracting', 'comparing'].includes(step) || (current >= 0 && project.progress.percent >= 75)
  return (
    <section className="panel space-y-4 p-5" aria-live="polite" aria-label="Fortschritt der Analyse">
      <div className="flex items-center justify-between gap-4">
        <p className="font-medium">{project.progress.message ?? 'Analyse läuft'}</p>
        <span className="text-sm text-muted-foreground tabular-nums">{project.progress.percent} %</span>
      </div>
      <Progress value={project.progress.percent} />
      {fullRun ? <ol className="grid gap-2 text-sm sm:grid-cols-3">
        {analysisSteps.map((step, index) => (
          <li key={step} className={cn('flex items-center gap-2', index > current && 'text-muted-foreground')}>
            {index < current ? <Check aria-hidden="true" className="size-4 text-ok" />
              : index === current ? <Loader2 aria-hidden="true" className="size-4 animate-spin" />
              : <span aria-hidden="true" className="size-4 rounded-full border" />}
            {stepLabels[step]}
          </li>
        ))}
      </ol> : null}
      <p className="text-xs text-muted-foreground">Ziel: unter 5 Minuten je Paket. Sie können die Seite verlassen, die Analyse läuft weiter.</p>
    </section>
  )
}
