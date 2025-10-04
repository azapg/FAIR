import {useMutation, useQuery, useQueryClient} from '@tanstack/react-query'
import api from '@/lib/api'
import {Grade} from "@/app/courses/tabs/assignments/assignments";

export type ListParams = Record<string, string | number | boolean | null | undefined>

export type Assignment = {
  id: string
  courseId: string

  title: string
  description?: string

  deadline?: string
  maxGrade?: Grade

  createdAt: string
  updatedAt: string
}

export type CreateAssignmentInput = {
  courseId: string
  title: string
  description?: string | null
  deadline?: string | null
  maxGrade?: Grade | null
  artifacts?: string[]  // Existing artifact IDs
  files?: File[]        // New files to upload
}

export type UpdateAssignmentInput = Partial<Omit<CreateAssignmentInput, 'courseId'>> & {
  artifacts?: string[]
}

export const assignmentsKeys = {
  all: ['assignments'] as const,
  lists: () => [...assignmentsKeys.all, 'list'] as const,
  list: (params?: ListParams) => [...assignmentsKeys.lists(), {params}] as const,
  details: () => [...assignmentsKeys.all, 'detail'] as const,
  detail: (id: string) => [...assignmentsKeys.details(), id] as const,
}

const fetchAssignments = async (params?: ListParams): Promise<Assignment[]> => {
  const res = await api.get('/assignments', {params})
  return res.data
}

const fetchAssignment = async (id: string): Promise<Assignment> => {
  const res = await api.get(`/assignments/${id}`)
  return res.data
}

const createAssignment = async (data: CreateAssignmentInput): Promise<Assignment> => {
  const formData = new FormData()
  formData.append('course_id', data.courseId)
  formData.append('title', data.title)

  if (data.description) {
    formData.append('description', data.description)
  }

  if (data.deadline) {
    formData.append('deadline', data.deadline)
  }

  if (data.maxGrade) {
    formData.append('max_grade', JSON.stringify(data.maxGrade))
  }

  if (data.artifacts && data.artifacts.length > 0) {
    formData.append('artifact_ids', JSON.stringify(data.artifacts))
  }

  if (data.files && data.files.length > 0) {
    data.files.forEach(file => {
      formData.append('files', file)
    })
  }

  const res = await api.post('/assignments', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  })
  return res.data
}

const updateAssignment = async (id: string, data: UpdateAssignmentInput): Promise<Assignment> => {
  const res = await api.put(`/assignments/${id}`, data)
  return res.data
}

const deleteAssignment = async (id: string): Promise<void> => {
  await api.delete(`/assignments/${id}`)
}

export function useAssignments(params?: ListParams, enabled = true) {
  return useQuery({
    queryKey: assignmentsKeys.list(params),
    queryFn: () => fetchAssignments(params),
    enabled,
  })
}

export function useAssignment(id?: string, enabled = true) {
  return useQuery({
    queryKey: id != null ? assignmentsKeys.detail(id) : assignmentsKeys.detail('unknown'),
    queryFn: () => fetchAssignment(id as string),
    enabled: enabled && id != null,
  })
}

export function useCreateAssignment() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: CreateAssignmentInput) => createAssignment(data),
    onSuccess: (assignment) => {
      // refresh list(s); callers may also refetch course-specific lists via params
      qc.invalidateQueries({queryKey: assignmentsKeys.lists()}).then()
      qc.invalidateQueries({queryKey: assignmentsKeys.detail(assignment.id)}).then()
    },
  })
}

export function useUpdateAssignment() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({id, data}: { id: string; data: UpdateAssignmentInput }) => updateAssignment(id, data),
    onSuccess: (_assignment, vars) => {
      qc.invalidateQueries({queryKey: assignmentsKeys.detail(vars.id)}).then()
      qc.invalidateQueries({queryKey: assignmentsKeys.lists()}).then()
    },
  })
}

export function useDeleteAssignment() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => deleteAssignment(id),
    onSuccess: (_void, id) => {
      qc.invalidateQueries({queryKey: assignmentsKeys.detail(id)}).then()
      qc.invalidateQueries({queryKey: assignmentsKeys.lists()}).then()
    },
  })
}

