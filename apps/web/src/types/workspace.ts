import type { IsoDateTime } from './common'

export type Workspace = {
  id: number
  name: string
  description?: string | null
  createdAt: IsoDateTime
  updatedAt: IsoDateTime
}
