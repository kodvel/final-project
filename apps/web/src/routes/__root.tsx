import { createRootRoute, HeadContent, Outlet, Scripts } from '@tanstack/react-router'

import { Sidebar } from '../components/layout/sidebar'
import { QueryProvider } from '../components/providers/query-provider'
import { WorkspaceSelector } from '../features/workspaces/components/workspace-selector'
import { WorkspaceProvider } from '../features/workspaces/hooks/use-active-workspace'
import '../app.css'

export const Route = createRootRoute({
  head: () => ({
    meta: [{ charSet: 'utf-8' }, { name: 'viewport', content: 'width=device-width, initial-scale=1' }, { title: 'Final Project' }],
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
            <div className="min-h-screen bg-[#F8F7FC] text-[#151826] md:flex">
              <Sidebar />
              <div className="min-w-0 flex-1">
                <header className="flex items-center justify-between border-b border-[#E5E2F0] bg-white px-6 py-4">
                  <div>
                    <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[#626A7C]">Company Intelligence Copilot</p>
                    <h1 className="text-xl font-semibold text-[#151826]">Company memory workspace</h1>
                  </div>
                  <WorkspaceSelector />
                </header>
                <Outlet />
              </div>
            </div>
          </WorkspaceProvider>
        </QueryProvider>
        <Scripts />
      </body>
    </html>
  )
}
