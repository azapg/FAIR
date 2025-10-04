import {useMutation, useQuery, useQueryClient} from '@tanstack/react-query'
import api from '@/lib/api'
import {Assignment} from "@/hooks/use-assignments";

export type Course = {
  id: string
  name: string
  description?: string | null
  instructor_id: string
  instructor_name?: string
  assignments_count: number
}

export type CourseDetail = {
  id: string,
  name: string,
  description?: string | null,
  instructor: {
    id: string,
    name: string,
    email: string,
    role: 'professor' | 'admin' | 'student',
  },
  assignments: Assignment[],
  workflows: {
    id: string,
    name: string,
    description?: string | null,
    created_at: string,
    updated_at: string,
  }
}

export type CreateCourseInput = {
  name: string
  description?: string | null
  instructor_id: string
}

export type UpdateCourseInput = Partial<Pick<Course, 'name' | 'description'>>

export type ListParams = Record<string, string | number | boolean | null | undefined>

export const coursesKeys = {
  all: ['courses'] as const,
  lists: () => [...coursesKeys.all, 'list'] as const,
  list: (params?: ListParams) => [...coursesKeys.lists(), {params}] as const,
  details: () => [...coursesKeys.all, 'detail'] as const,
  detail: (id: string) => [...coursesKeys.details(), id] as const,
}

const fetchCourses = async (params?: ListParams): Promise<Course[]> => {
  const res = await api.get('/courses', {params})
  return res.data
}

const fetchCourse = async (id: string, detailed: boolean = false): Promise<Course | CourseDetail> => {
  const res = await api.get(`/courses/${id}?detailed=${detailed}`)
  return res.data
}

const createCourse = async (data: CreateCourseInput): Promise<Course> => {
  const res = await api.post('/courses', data)
  return res.data
}

const updateCourse = async (id: string, data: UpdateCourseInput): Promise<Course> => {
  const res = await api.put(`/courses/${id}`, data)
  return res.data
}

const deleteCourse = async (id: string): Promise<void> => {
  await api.delete(`/courses/${id}`)
}

export function useCourses(params?: ListParams, enabled = true) {
  return useQuery({
    queryKey: coursesKeys.list(params),
    queryFn: () => fetchCourses(params),
    enabled,
  })
}

export function useCourse(id?: string, enabled = true, detailed = false) {
  return useQuery({
    queryKey: id != null
      ? [...coursesKeys.detail(id), {detailed}]
      : [...coursesKeys.detail('unknown'), {detailed}],
    queryFn: () => fetchCourse(id as string, detailed),
    enabled: enabled && id != null,
  })
}

export function useCreateCourse() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: CreateCourseInput) => createCourse(data),
    onSuccess: () => {
      qc.invalidateQueries({queryKey: coursesKeys.lists()}).then()
    },
  })
}

export function useUpdateCourse() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({id, data}: { id: string; data: UpdateCourseInput }) => updateCourse(id, data),
    onSuccess: (_course, vars) => {
      qc.invalidateQueries({queryKey: coursesKeys.detail(vars.id)}).then()
      qc.invalidateQueries({queryKey: coursesKeys.lists()}).then()
    },
  })
}

export function useDeleteCourse() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => deleteCourse(id),
    onSuccess: (_void, id) => {
      qc.invalidateQueries({queryKey: coursesKeys.detail(id)}).then()
      qc.invalidateQueries({queryKey: coursesKeys.lists()}).then()
    },
  })
}
