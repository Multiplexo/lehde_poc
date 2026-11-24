import { createRootRoute, Link, Outlet } from '@tanstack/react-router'
import { FlaskConical } from 'lucide-react'
import { FeedbackButton } from '@/components/feedback-button'
import { TooltipProvider } from '@/components/ui/tooltip'
import { brand } from '@/lib/brand'

export const Route = createRootRoute({
  component: RootLayout,
  notFoundComponent: () => (
    <div className="space-y-3">
      <h1 className="text-2xl font-semibold">Seite nicht gefunden</h1>
      <Link to="/" className="underline">Zur Übersicht</Link>
    </div>
  ),
})

function RootLayout() {
  return (
    <TooltipProvider>
      <header className="sticky top-0 z-30 border-b bg-brand text-brand-foreground">
        <div className="mx-auto flex h-14 max-w-[1600px] items-center gap-6 px-4 md:px-8">
          <Link to="/" className="flex items-center gap-2.5 font-semibold tracking-tight">
            <span aria-hidden="true" className="grid size-7 place-items-center rounded-md bg-brand-accent text-sm font-bold text-brand">{brand.customer.slice(0, 1)}</span>
            <span>{brand.customer}</span>
            <span className="font-normal opacity-70">{brand.product}</span>
          </Link>
          <nav aria-label="Hauptnavigation" className="flex items-center gap-1 text-sm">
            <Link to="/" activeOptions={{ exact: true }} className="rounded-md px-3 py-1.5 opacity-80 hover:bg-white/10 hover:opacity-100 data-[status=active]:bg-white/15 data-[status=active]:opacity-100">Anfragepakete</Link>
            <Link to="/feedback" className="rounded-md px-3 py-1.5 opacity-80 hover:bg-white/10 hover:opacity-100 data-[status=active]:bg-white/15 data-[status=active]:opacity-100">Feedback</Link>
          </nav>
          <span className="ml-auto inline-flex items-center gap-1.5 rounded-full border border-brand-accent/60 px-3 py-1 text-xs text-brand-accent" title="Gesprächsinstrument zum Schärfen der Anforderungen, kein Produktivsystem">
            <FlaskConical aria-hidden="true" className="size-3.5" />Prototyp – kein Produktivsystem
          </span>
        </div>
      </header>
      <main className="mx-auto w-full max-w-[1600px] px-4 py-6 md:px-8 md:py-8">
        <Outlet />
      </main>
      <FeedbackButton />
    </TooltipProvider>
  )
}
