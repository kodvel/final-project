import { apiFetch } from '../../lib/api-client'
import type { DecisionApprovalStatus, DecisionBrief, DecisionBriefApi } from '../../types/decision-brief'

function briefFromApi(brief: DecisionBriefApi): DecisionBrief {
  return {
    id: brief.id,
    workspaceId: brief.workspace_id,
    chatSessionId: brief.chat_session_id,
    chatMessageId: brief.chat_message_id,
    sequenceNumber: brief.sequence_number,
    contextCutoffMessageId: brief.context_cutoff_message_id,
    title: brief.title,
    objective: brief.objective,
    recommendationStatus: brief.recommendation_status,
    approvalStatus: brief.approval_status,
    contentJson: brief.content_json,
    createdAt: brief.created_at,
    updatedAt: brief.updated_at,
    statusUpdatedAt: brief.status_updated_at,
  }
}

export async function getDecisionBrief(briefId: number, workspaceId: number): Promise<DecisionBrief> {
  return briefFromApi(
    await apiFetch<DecisionBriefApi>(`/decision-briefs/${briefId}?workspace_id=${workspaceId}`),
  )
}

export async function updateDecisionBriefStatus(
  briefId: number,
  workspaceId: number,
  approvalStatus: DecisionApprovalStatus,
): Promise<DecisionBrief> {
  return briefFromApi(
    await apiFetch<DecisionBriefApi>(`/decision-briefs/${briefId}/status`, {
      method: 'PATCH',
      body: JSON.stringify({ workspace_id: workspaceId, approval_status: approvalStatus }),
    }),
  )
}
