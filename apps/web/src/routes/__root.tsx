import { createRootRoute, HeadContent, Outlet, Scripts } from '@tanstack/react-router'

import { QueryProvider } from '../components/providers/query-provider'
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
          <Outlet />
        </QueryProvider>
        <Scripts />
      </body>
    </html>
  )
}
