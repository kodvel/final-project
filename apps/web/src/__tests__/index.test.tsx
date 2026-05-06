import { renderToString } from 'react-dom/server'
import { describe, expect, it } from 'vitest'

import { ChatPage } from '../routes/chat'

describe('ChatPage', () => {
  it('renders the Intelligence Copilot chat surface', () => {
    expect(renderToString(<ChatPage />)).toContain('Intelligence Copilot')
  })
})
