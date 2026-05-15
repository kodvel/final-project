import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import type { DecisionApprovalStatus, DecisionBrief } from '../../../types/decision-brief'
import { getDecisionBrief, listDecisionBriefs, updateDecisionBriefStatus } from '../api'

export function useDecisionBrief(briefId: number | null, workspaceId: number | null) {
  return useQuery({
    queryKey: ['decision-brief', briefId, workspaceId],
    queryFn: () => getDecisionBrief(briefId ?? 0, workspaceId ?? 0),
    enabled: typeof briefId === 'number' && briefId > 0 && typeof workspaceId === 'number' && workspaceId > 0,
  })
}

export function useDecisionBriefs(workspaceId: number | null, approvalStatus?: DecisionApprovalStatus) {
  return useQuery({
    queryKey: ['decision-briefs', workspaceId, approvalStatus ?? 'all'],
    queryFn: () => listDecisionBriefs(workspaceId ?? 0, approvalStatus),
    enabled: typeof workspaceId === 'number' && workspaceId > 0,
  })
}

export function useUpdateDecisionBriefStatus() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ briefId, workspaceId, approvalStatus }: { briefId: number; workspaceId: number; approvalStatus: DecisionApprovalStatus }) =>
      updateDecisionBriefStatus(briefId, workspaceId, approvalStatus),
    onSuccess: (brief: DecisionBrief) => {
      queryClient.invalidateQueries({ queryKey: ['decision-brief', brief.id, brief.workspaceId] })
      queryClient.invalidateQueries({ queryKey: ['chat-session', brief.chatSessionId, brief.workspaceId] })
      queryClient.invalidateQueries({ queryKey: ['decision-briefs', brief.workspaceId] })
    },
  })
}
