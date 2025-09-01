'use client'

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import api from '@/lib/api'

export type Id = string | number
export type ListParams = Record<string, string | number | boolean | null | undefined>

export type Artifact = {
  id: Id
  title: string
  artifact_type: string
  mime: string
  storage_path: string
  storage_type: string
  meta?: Record<string, unknown> | null
}

export type CreateArtifactInput = {
  title: string
  artifact_type: string
  mime: string
  storage_path: string
  storage_type: string
  meta?: Record<string, unknown> | null
}

export type UpdateArtifactInput = Partial<CreateArtifactInput>

export const artifactsKeys = {
  all: ['artifacts'] as const,
  lists: () => [...artifactsKeys.all, 'list'] as const,
  list: (params?: ListParams) => [...artifactsKeys.lists(), { params }] as const,
  details: () => [...artifactsKeys.all, 'detail'] as const,
  detail: (id: Id) => [...artifactsKeys.details(), id] as const,
}

const fetchArtifacts = async (params?: ListParams): Promise<Artifact[]> => {
  const res = await api.get('/artifacts', { params })
  return res.data
}

const fetchArtifact = async (id: Id): Promise<Artifact> => {
  const res = await api.get(`/artifacts/${id}`)
  return res.data
}

const createArtifact = async (data: CreateArtifactInput): Promise<Artifact> => {
  const res = await api.post('/artifacts', data)
  return res.data
}

const updateArtifact = async (id: Id, data: UpdateArtifactInput): Promise<Artifact> => {
  const res = await api.put(`/artifacts/${id}`, data)
  return res.data
}

const deleteArtifact = async (id: Id): Promise<void> => {
  await api.delete(`/artifacts/${id}`)
}

export function useArtifacts(params?: ListParams, enabled = true) {
  return useQuery({
    queryKey: artifactsKeys.list(params),
    queryFn: () => fetchArtifacts(params),
    enabled,
  })
}

export function useArtifact(id?: Id, enabled = true) {
  return useQuery({
    queryKey: id != null ? artifactsKeys.detail(id) : artifactsKeys.detail('unknown'),
    queryFn: () => fetchArtifact(id as Id),
    enabled: enabled && id != null,
  })
}

export function useCreateArtifact() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: CreateArtifactInput) => createArtifact(data),
    onSuccess: (artifact) => {
      qc.invalidateQueries({ queryKey: artifactsKeys.lists() }).then()
      qc.invalidateQueries({ queryKey: artifactsKeys.detail(artifact.id) }).then()
    },
  })
}

export function useUpdateArtifact() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }: { id: Id; data: UpdateArtifactInput }) => updateArtifact(id, data),
    onSuccess: (_artifact, vars) => {
      qc.invalidateQueries({ queryKey: artifactsKeys.detail(vars.id) }).then()
      qc.invalidateQueries({ queryKey: artifactsKeys.lists() }).then()
    },
  })
}

export function useDeleteArtifact() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: Id) => deleteArtifact(id),
    onSuccess: (_void, id) => {
      qc.invalidateQueries({ queryKey: artifactsKeys.detail(id) }).then()
      qc.invalidateQueries({ queryKey: artifactsKeys.lists() }).then()
    },
  })
}

