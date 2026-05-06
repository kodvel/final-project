import { createRootRoute, HeadContent, Outlet, Scripts } from '@tanstack/react-router'

import { Sidebar } from '../components/layout/sidebar'
import { QueryProvider } from '../components/providers/query-provider'
import { TooltipProvider } from '../components/ui/tooltip'
import { WorkspaceProvider } from '../features/workspaces/hooks/use-active-workspace'
import '../app.css'

export const Route = createRootRoute({
  head: () => ({
    meta: [{ charSet: 'utf-8' }, { name: 'viewport', content: 'width=device-width, initial-scale=1' }, { title: 'Company Intelligence Copilot' }],
    links: [],
  }),
  component: RootDocument,
})

function RootDocument() {
  return (
    <html lang="en">
      <head>
        <HeadContent />
      </head>
      <body>
        <QueryProvider>
          <WorkspaceProvider>
            <TooltipProvider>
              <div className="flex h-screen overflow-hidden bg-[#12151C] font-[family-name:var(--font-body)] text-[var(--foreground)]">
                <Sidebar />
                <main className="m-6 ml-0 flex-1 overflow-hidden rounded-3xl bg-white shadow-[0_8px_40px_rgba(0,0,0,0.25)]">
                  <Outlet />
                </main>
              </div>
            </TooltipProvider>
          </WorkspaceProvider>
        </QueryProvider>
        <Scripts />
      </body>
    </html>
  )
}
