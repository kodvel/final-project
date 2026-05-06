import { renderToString } from 'react-dom/server'
import { describe, expect, it } from 'vitest'

import { QueryProvider } from '../components/providers/query-provider'
import { WorkspaceProvider } from '../features/workspaces/hooks/use-active-workspace'
import { ChatPage } from '../routes/chat'

describe('ChatPage', () => {
  it('renders the Intelligence Copilot chat surface', () => {
    expect(
      renderToString(
        <QueryProvider>
          <WorkspaceProvider>
            <ChatPage />
          </WorkspaceProvider>
        </QueryProvider>,
      ),
    ).toContain('Start a Workspace-scoped Chat Session')
  })
})
