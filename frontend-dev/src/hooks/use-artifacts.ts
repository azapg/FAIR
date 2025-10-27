
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import api from '@/lib/api'
import { toast } from 'sonner';

export type ListParams = Record<string, string | number | boolean | null | undefined>

export type Artifact = {
  id: string
  title: string
  storagePath: string
  storageType: string
  creatorId: string
  createdAt: string
  updatedAt: string
  status: string
  courseId?: string | null
  assignmentId?: string | null
  accessLevel: string
  meta?: Record<string, unknown> | null
}

export type CreateArtifactInput = {
  title: string
  creatorId?: string | null
  courseId?: string | null
  assignmentId?: string | null
  accessLevel?: string | null
  status?: string | null
  meta?: Record<string, unknown> | null
}

export type UpdateArtifactInput = {
  title?: string | null
  courseId?: string | null
  assignmentId?: string | null
  accessLevel?: string | null
  status?: string | null
  meta?: Record<string, unknown> | null
}

export type ArtifactsListParams = {
  creatorId?: string
  courseId?: string
  assignmentId?: string
  status?: string
  accessLevel?: string
}

export const artifactsKeys = {
  all: ['artifacts'] as const,
  lists: () => [...artifactsKeys.all, 'list'] as const,
  list: (params?: ArtifactsListParams) => [...artifactsKeys.lists(), { params }] as const,
  details: () => [...artifactsKeys.all, 'detail'] as const,
  detail: (id: string) => [...artifactsKeys.details(), id] as const,
}

const fetchArtifacts = async (params?: ArtifactsListParams): Promise<Artifact[]> => {
  const queryParams: Record<string, string> = {}
  if (params?.creatorId) queryParams.creator_id = params.creatorId.toString()
  if (params?.courseId) queryParams.course_id = params.courseId.toString()
  if (params?.assignmentId) queryParams.assignment_id = params.assignmentId.toString()
  if (params?.status) queryParams.status = params.status
  if (params?.accessLevel) queryParams.access_level = params.accessLevel

  const res = await api.get('/artifacts', { params: queryParams })
  return res.data
}

const fetchArtifact = async (id: string): Promise<Artifact> => {
  const res = await api.get(`/artifacts/${id}`)
  return res.data
}

const createArtifact = async (data: CreateArtifactInput): Promise<Artifact> => {
  const res = await api.post('/artifacts', data)
  return res.data
}

const updateArtifact = async (id: string, data: UpdateArtifactInput): Promise<Artifact> => {
  const res = await api.put(`/artifacts/${id}`, data)
  return res.data
}

const deleteArtifact = async (id: string): Promise<void> => {
  await api.delete(`/artifacts/${id}`)
}

export function useArtifacts(params?: ArtifactsListParams, enabled = true) {
  return useQuery({
    queryKey: artifactsKeys.list(params),
    queryFn: () => fetchArtifacts(params),
    enabled,
  })
}

export function useArtifact(id?: string, enabled = true) {
  return useQuery({
    queryKey: id != null ? artifactsKeys.detail(id) : artifactsKeys.detail('unknown'),
    queryFn: () => fetchArtifact(id as string),
    enabled: enabled && id != null,
  })
}

export function useCreateArtifact() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: CreateArtifactInput) => createArtifact(data),
    onSuccess: (artifact) => {
      qc.invalidateQueries({ queryKey: artifactsKeys.lists() })
      qc.invalidateQueries({ queryKey: artifactsKeys.detail(artifact.id) })
      toast.success('Artifact created successfully', { description: artifact.title });
    },
    onError: (error: Error) => {
      toast.error('Failed to create artifact', {
        description: error.message || 'Something went wrong'
      });
    }
  })
}

export function useUpdateArtifact() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: UpdateArtifactInput }) => updateArtifact(id, data),
    onSuccess: (_artifact, vars) => {
      qc.invalidateQueries({ queryKey: artifactsKeys.detail(vars.id) })
      qc.invalidateQueries({ queryKey: artifactsKeys.lists() })
      toast.success('Artifact updated successfully');
    },
    onError: (error: Error) => {
      toast.error('Failed to update artifact', {
        description: error.message || 'Something went wrong'
      });
    }
  })
}

export function useDeleteArtifact() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => deleteArtifact(id),
    onSuccess: (_void, id) => {
      qc.invalidateQueries({ queryKey: artifactsKeys.detail(id) })
      qc.invalidateQueries({ queryKey: artifactsKeys.lists() })
      toast.success('Artifact deleted Successfully', {
        description: 'The artifact has been permanently removed'
      })
    },
    onError: (error: Error) => {
      toast.error('Failed to delete artifact', {
        description: error.message || 'Something went wrong'
      });
    }
  })
}