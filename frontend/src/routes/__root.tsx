import { createRootRoute, Link, Outlet } from '@tanstack/react-router'
import { FlaskConical } from 'lucide-react'
import { BrandLogo } from '@/components/brand-logo'
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
      <header className="sticky top-0 z-30 border-b-4 border-brand-accent bg-card text-foreground shadow-sm">
        <div className="mx-auto flex h-16 max-w-[1600px] items-center gap-8 px-4 md:px-8">
          <Link to="/" className="flex items-center gap-3" aria-label={`${brand.customer} ${brand.product}, zur Übersicht`}>
            <BrandLogo />
            <span className="text-lg font-medium text-muted-foreground">{brand.product}</span>
          </Link>
          <nav aria-label="Hauptnavigation" className="flex items-center gap-6 text-[15px]">
            <Link to="/" activeOptions={{ exact: true }} className="py-1 text-muted-foreground hover:text-foreground data-[status=active]:font-semibold data-[status=active]:text-foreground">Anfragepakete</Link>
            <Link to="/feedback" className="py-1 text-muted-foreground hover:text-foreground data-[status=active]:font-semibold data-[status=active]:text-foreground">Feedback</Link>
          </nav>
          <span className="ml-auto inline-flex items-center gap-1.5 rounded-full bg-brand px-3 py-1 text-xs text-brand-accent" title="Gesprächsinstrument zum Schärfen der Anforderungen, kein Produktivsystem">
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
