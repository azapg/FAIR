
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import api from '@/lib/api'
import {Grade} from "@/app/demo/courses/[...id]/tabs/assignments/assignments";

export type Id = string | number
export type ListParams = Record<string, string | number | boolean | null | undefined>

export type Assignment = {
  id: Id
  course_id: Id
  title: string
  description?: string | null
  deadline: string | null
  max_grade?: Grade | null
}

export type AssignmentArtifactLink = {
  artifact_id: Id
  role: string | null
}

export type CreateAssignmentInput = {
  course_id: Id
  title: string
  description?: string | null
  deadline?: string | null
  max_grade?: Grade | null
  artifacts?: AssignmentArtifactLink[]
}

export type UpdateAssignmentInput = Partial<Omit<CreateAssignmentInput, 'course_id'>> & {
  artifacts?: AssignmentArtifactLink[]
}

export const assignmentsKeys = {
  all: ['assignments'] as const,
  lists: () => [...assignmentsKeys.all, 'list'] as const,
  list: (params?: ListParams) => [...assignmentsKeys.lists(), { params }] as const,
  details: () => [...assignmentsKeys.all, 'detail'] as const,
  detail: (id: Id) => [...assignmentsKeys.details(), id] as const,
}

const fetchAssignments = async (params?: ListParams): Promise<Assignment[]> => {
  const res = await api.get('/assignments', { params })
  return res.data
}

const fetchAssignment = async (id: Id): Promise<Assignment> => {
  const res = await api.get(`/assignments/${id}`)
  return res.data
}

const createAssignment = async (data: CreateAssignmentInput): Promise<Assignment> => {
  const res = await api.post('/assignments', data)
  return res.data
}

const updateAssignment = async (id: Id, data: UpdateAssignmentInput): Promise<Assignment> => {
  const res = await api.put(`/assignments/${id}`, data)
  return res.data
}

const deleteAssignment = async (id: Id): Promise<void> => {
  await api.delete(`/assignments/${id}`)
}

export function useAssignments(params?: ListParams, enabled = true) {
  return useQuery({
    queryKey: assignmentsKeys.list(params),
    queryFn: () => fetchAssignments(params),
    enabled,
  })
}

export function useAssignment(id?: Id, enabled = true) {
  return useQuery({
    queryKey: id != null ? assignmentsKeys.detail(id) : assignmentsKeys.detail('unknown'),
    queryFn: () => fetchAssignment(id as Id),
    enabled: enabled && id != null,
  })
}

export function useCreateAssignment() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: CreateAssignmentInput) => createAssignment(data),
    onSuccess: (assignment) => {
      // refresh list(s); callers may also refetch course-specific lists via params
      qc.invalidateQueries({ queryKey: assignmentsKeys.lists() }).then()
      qc.invalidateQueries({ queryKey: assignmentsKeys.detail(assignment.id) }).then()
    },
  })
}

export function useUpdateAssignment() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }: { id: Id; data: UpdateAssignmentInput }) => updateAssignment(id, data),
    onSuccess: (_assignment, vars) => {
      qc.invalidateQueries({ queryKey: assignmentsKeys.detail(vars.id) }).then()
      qc.invalidateQueries({ queryKey: assignmentsKeys.lists() }).then()
    },
  })
}

export function useDeleteAssignment() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: Id) => deleteAssignment(id),
    onSuccess: (_void, id) => {
      qc.invalidateQueries({ queryKey: assignmentsKeys.detail(id) }).then()
      qc.invalidateQueries({ queryKey: assignmentsKeys.lists() }).then()
    },
  })
}

