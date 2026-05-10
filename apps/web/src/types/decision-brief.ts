import type { IsoDateTime } from './common'

export type DecisionRecommendationStatus = 'go' | 'no_go' | 'validate_first'
export type DecisionApprovalStatus = 'draft' | 'reviewed' | 'approved' | 'rejected'

export type DecisionBriefContentJson = {
  context_problem: string
  source_evidence: string
  strategic_interpretation: string
  recommendation: string
  alternatives_considered: string
  risks_assumptions: string
  success_metrics: string
  next_steps: string
}

export type DecisionBrief = {
  id: number
  workspaceId: number
  chatSessionId: number
  chatMessageId: number
  title: string
  recommendationStatus: DecisionRecommendationStatus
  approvalStatus: DecisionApprovalStatus
  contentJson: DecisionBriefContentJson
  createdAt: IsoDateTime
  updatedAt: IsoDateTime
}

export type DecisionBriefApi = {
  id: number
  workspace_id: number
  chat_session_id: number
  chat_message_id: number
  title: string
  recommendation_status: DecisionRecommendationStatus
  approval_status: DecisionApprovalStatus
  content_json: DecisionBriefContentJson
  created_at: IsoDateTime
  updated_at: IsoDateTime
}
