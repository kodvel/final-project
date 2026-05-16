import type { IsoDateTime } from './common'

export type Workspace = {
  id: number
  name: string
  description?: string | null
  createdAt: IsoDateTime
  updatedAt: IsoDateTime
}

export type CreateWorkspaceInput = {
  name: string
  description?: string
}

export type UpdateWorkspaceInput = {
  name?: string
  description?: string | null
}

export type WorkspaceListItem = Pick<Workspace, 'id' | 'name' | 'description'>

export type WorkspaceApi = {
  id: number
  name: string
  description?: string | null
  created_at: IsoDateTime
  updated_at: IsoDateTime
}
