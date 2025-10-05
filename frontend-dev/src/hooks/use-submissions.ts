import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import api from '@/lib/api'
import { toast } from 'sonner'

export type ListParams = Record<string, string | number | boolean | null | undefined>

export type SubmissionStatus =
  | "pending"
  | "submitted"
  | "transcribing"
  | "transcribed"
  | "grading"
  | "graded"
  | "needs_review"
  | "failure"

export type Artifact = {
  id: string
  title: string
  content_type: string
  created_at: string
}

export type Submitter = {
  id: string
  name: string
  email: string
  role: string
}

export type Submission = {
  id: string
  assignment_id: string
  submitter_id: string
  submitter?: Submitter
  submitted_at: string
  status: SubmissionStatus
  official_run_id?: string | null
  artifacts: Artifact[]
}

export type CreateSubmissionInput = {
  assignment_id: string
  submitter_name: string
  artifact_ids?: string[]  // Existing artifact IDs
  files?: File[]           // New files to upload
}

export type UpdateSubmissionInput = {
  submitted_at?: string
  status?: SubmissionStatus
  official_run_id?: string | null
  artifact_ids?: string[]
}

export const submissionsKeys = {
  all: ['submissions'] as const,
  lists: () => [...submissionsKeys.all, 'list'] as const,
  list: (params?: ListParams) => [...submissionsKeys.lists(), { params }] as const,
  details: () => [...submissionsKeys.all, 'detail'] as const,
  detail: (id: string) => [...submissionsKeys.details(), id] as const,
}

const fetchSubmissions = async (params?: ListParams): Promise<Submission[]> => {
  const res = await api.get('/submissions', { params })
  return res.data
}

const fetchSubmission = async (id: string): Promise<Submission> => {
  const res = await api.get(`/submissions/${id}`)
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
