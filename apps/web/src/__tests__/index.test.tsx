import { renderToString } from 'react-dom/server'
import { describe, expect, it } from 'vitest'

import { HomePage } from '../routes/index'

describe('HomePage', () => {
  it('renders the foundation template title', () => {
    expect(renderToString(<HomePage />)).toContain('Final Project')
  })
})
