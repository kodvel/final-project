import type { IsoDateTime } from './common'

export type DecisionRecommendationStatus = 'go' | 'no_go' | 'validate_first'
export type DecisionApprovalStatus = 'draft' | 'reviewed' | 'approved' | 'rejected'

export type DecisionBrief = {
  id: number
  workspaceId: number
  chatSessionId: number
  chatMessageId: number
  title: string
  recommendationStatus: DecisionRecommendationStatus
  approvalStatus: DecisionApprovalStatus
  contentJson: Record<string, unknown>
  createdAt: IsoDateTime
  updatedAt: IsoDateTime
}
