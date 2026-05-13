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
  sequenceNumber: number
  title: string
  objective: string | null
  recommendationStatus: DecisionRecommendationStatus
  approvalStatus: DecisionApprovalStatus
  contentJson: DecisionBriefContentJson
  contextCutoffMessageId: number | null
  statusUpdatedAt: IsoDateTime | null
  createdAt: IsoDateTime
  updatedAt: IsoDateTime
}

export type DecisionBriefApi = {
  id: number
  workspace_id: number
  chat_session_id: number
  chat_message_id: number
  sequence_number: number
  title: string
  objective: string | null
  recommendation_status: DecisionRecommendationStatus
  approval_status: DecisionApprovalStatus
  content_json: DecisionBriefContentJson
  context_cutoff_message_id: number | null
  status_updated_at: IsoDateTime | null
  created_at: IsoDateTime
  updated_at: IsoDateTime
}
