import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import api from '@/lib/api'
import { Artifact } from "@/hooks/use-artifacts"
import { toast } from 'sonner'
import { AuthUser } from "@/contexts/auth-context"
import { WorkflowRun } from "@/store/workflows-store"

export type SubmissionEventType =
  | "ai_graded"
  | "initial_result"
  | "manual_edit"
  | "returned"
  | "status_changed"

export type SubmissionEvent = {
  id: string
  submissionId: string
  eventType: SubmissionEventType
  actor?: AuthUser | null
  workflowRun?: WorkflowRun | null
  details?: Record<string, unknown> | null
  createdAt: string
}

export type ListParams = Record<string, string | number | boolean | null | undefined>

export type SubmissionStatus =
  | "pending"
  | "submitted"
  | "transcribing"
  | "transcribed"
  | "grading"
  | "graded"
  | "returned"
  | "excused"
  | "needs_review"
  | "failure"
  | "processing"

export type Submitter = {
  id: string
  name: string
  email: string
  role: string
}

export type SubmissionResult = {
  id: string
  submissionId: string
  workflowRunId: string

  transcription?: string | null
  transcriptionConfidence?: number | null
  transcribedAt?: string | null

  score?: number | null
  feedback?: string | null
  gradedAt?: string | null
  gradingMeta?: Record<string, unknown> | null
}

export type Submission = {
  id: string
  assignmentId: string
  submitterId: string
  submitter?: Submitter
  submittedAt: string
  status: SubmissionStatus
  officialRunId?: string | null
  officialResult?: SubmissionResult | null
  draftScore?: number | null
  draftFeedback?: string | null
  publishedScore?: number | null
  publishedFeedback?: string | null
  returnedAt?: string | null
  artifacts: Artifact[]
}

export type CreateSubmissionInput = {
  assignment_id: string
  submitter_name: string
  artifact_ids?: string[]  // Existing artifact IDs
  files?: File[]           // New files to upload
}

export type UpdateSubmissionInput = {
  artifact_ids?: string[]
}

export type UpdateSubmissionDraftInput = {
  score?: number | null
  feedback?: string | null
}

export const submissionsKeys = {
  all: ['submissions'] as const,
  lists: () => [...submissionsKeys.all, 'list'] as const,
  list: (params?: ListParams) => [...submissionsKeys.lists(), { params }] as const,
  details: () => [...submissionsKeys.all, 'detail'] as const,
  detail: (id: string) => [...submissionsKeys.details(), id] as const,
  timeline: (id?: string) => [...submissionsKeys.detail(id || ''), 'timeline'] as const,
}

const fetchSubmissions = async (params?: ListParams): Promise<Submission[]> => {
  const res = await api.get('/submissions', { params })
  return res.data
}

const fetchSubmission = async (id: string): Promise<Submission> => {
  const res = await api.get(`/submissions/${id}`)
  return res.data
}

const fetchSubmissionTimeline = async (id: string): Promise<SubmissionEvent[]> => {
  const res = await api.get(`/submissions/${id}/timeline`)
  return res.data
}

const createSubmission = async (data: CreateSubmissionInput): Promise<Submission> => {
  const formData = new FormData()

  formData.append('assignment_id', data.assignment_id)
  formData.append('submitter_name', data.submitter_name)

  if (data.artifact_ids && data.artifact_ids.length > 0) {
    formData.append('artifact_ids', JSON.stringify(data.artifact_ids))
  }

  if (data.files && data.files.length > 0) {
    data.files.forEach(file => {
      formData.append('files', file)
    })
  }

  const res = await api.post('/submissions', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  })
  return res.data
}

const updateSubmission = async (id: string, data: UpdateSubmissionInput): Promise<Submission> => {
  const res = await api.put(`/submissions/${id}`, data)
  return res.data
}

const updateSubmissionDraft = async (
  id: string,
  data: UpdateSubmissionDraftInput
): Promise<Submission> => {
  const res = await api.patch(`/submissions/${id}/draft`, data)
  return res.data
}

const returnSubmission = async (id: string): Promise<Submission> => {
  const res = await api.post(`/submissions/${id}/return`)
  return res.data
}

const deleteSubmission = async (id: string): Promise<void> => {
  await api.delete(`/submissions/${id}`)
}

// Hooks

export function useSubmissions(params?: ListParams) {
  return useQuery({
    queryKey: submissionsKeys.list(params),
    queryFn: () => fetchSubmissions(params),
  })
}

export function useSubmission(id: string) {
  return useQuery({
    queryKey: submissionsKeys.detail(id),
    queryFn: () => fetchSubmission(id),
    enabled: !!id,
  })
}

export function useSubmissionTimeline(id?: string) {
  return useQuery({
    queryKey: submissionsKeys.timeline(id),
    queryFn: () => fetchSubmissionTimeline(id!),
    enabled: !!id,
  })
}

export function useCreateSubmission() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: createSubmission,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: submissionsKeys.lists() })
      toast.success('Submission create successfully');
    },
    onError: (error: Error) => {
      toast.error('Failed to create Submission', {
        description: error.message || 'Something went wrong'
      });
    }
  })
}

export function useUpdateSubmission() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: UpdateSubmissionInput }) =>
      updateSubmission(id, data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: submissionsKeys.detail(variables.id) })
      queryClient.invalidateQueries({ queryKey: submissionsKeys.lists() })
      toast.success('Submission updated successfully');
    },
    onError: (error: Error) => {
      toast.error('Failed to update Submission', {
        description: error.message || 'Something went wrong'
      });
    }
  })
}

export function useUpdateSubmissionDraft() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: UpdateSubmissionDraftInput }) =>
      updateSubmissionDraft(id, data),
    onMutate: async (variables) => {
      // Cancel any outgoing refetches (so they don't overwrite our optimistic update)
      await queryClient.cancelQueries({ queryKey: submissionsKeys.lists() })
      await queryClient.cancelQueries({ queryKey: submissionsKeys.detail(variables.id) })

      // Snapshot the previous value
      const previousSubmission = queryClient.getQueryData<Submission>(
        submissionsKeys.detail(variables.id),
      )

      // Optimistically update the detail query
      if (previousSubmission) {
        queryClient.setQueryData<Submission>(submissionsKeys.detail(variables.id), {
          ...previousSubmission,
          draftScore:
            variables.data.score !== undefined
              ? variables.data.score
              : previousSubmission.draftScore,
          draftFeedback:
            variables.data.feedback !== undefined
              ? variables.data.feedback
              : previousSubmission.draftFeedback,
        })
      }

      // Also optimistically update the list queries
      queryClient.setQueriesData<Submission[]>(
        { queryKey: submissionsKeys.lists() },
        (old) => {
          if (!old) return old
          return old.map((s) => {
            if (s.id === variables.id) {
              return {
                ...s,
                draftScore:
                  variables.data.score !== undefined
                    ? variables.data.score
                    : s.draftScore,
                draftFeedback:
                  variables.data.feedback !== undefined
                    ? variables.data.feedback
                    : s.draftFeedback,
              }
            }
            return s
          })
        },
      )

      return { previousSubmission }
    },
    onSuccess: (_, variables) => {
      toast.success('Submission draft updated successfully')
    },
    onError: (error: Error, variables, context) => {
      // Rollback to the previous value if mutation fails
      if (context?.previousSubmission) {
        queryClient.setQueryData(
          submissionsKeys.detail(variables.id),
          context.previousSubmission,
        )
      }
      // Note: Rolling back the list is more complex if we want to be precise,
      // but invalidating them below will fix it anyway.

      toast.error('Failed to update submission draft', {
        description: error.message || 'Something went wrong',
      })
    },
    onSettled: (_, __, variables) => {
      // Always refetch after error or success to ensure we have the correct data
      queryClient.invalidateQueries({
        queryKey: submissionsKeys.detail(variables.id),
      })
      queryClient.invalidateQueries({ queryKey: submissionsKeys.lists() })
    },
  })
}

export function useReturnSubmission() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (id: string) => returnSubmission(id),
    onSuccess: (_, submissionId) => {
      queryClient.invalidateQueries({ queryKey: submissionsKeys.detail(submissionId) })
      queryClient.invalidateQueries({ queryKey: submissionsKeys.lists() })
      toast.success('Submission returned successfully');
    },
    onError: (error: Error) => {
      toast.error('Failed to return submission', {
        description: error.message || 'Something went wrong'
      });
    }
  })
}

export function useReturnSubmissions() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (ids: string[]) => {
      const results = await Promise.all(ids.map((id) => returnSubmission(id)))
      return results
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: submissionsKeys.lists() })
      toast.success('Submissions returned successfully');
    },
    onError: (error: Error) => {
      toast.error('Failed to return submissions', {
        description: error.message || 'Something went wrong'
      });
    }
  })
}

export function useDeleteSubmission() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: deleteSubmission,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: submissionsKeys.lists() })
      toast.success('Submission deleted successfully');
    },
    onError: (error: Error) => {
      toast.error('Failed to delete Submission', {
        description: error.message || 'Something went wrong'
      });
    }
  })
}
