'use client'

import {useMutation, useQuery, useQueryClient} from '@tanstack/react-query'
import api from '@/lib/api'

export type Id = string | number

export type Course = {
  id: Id
  name: string
  description?: string | null
  instructor_id: Id
  instructor_name?: string
  assignments_count: number
}

export type CreateCourseInput = {
  name: string
  description?: string | null
  instructor_id: Id
}

export type UpdateCourseInput = Partial<Pick<Course, 'name' | 'description'>>

export type ListParams = Record<string, string | number | boolean | null | undefined>

export const coursesKeys = {
  all: ['courses'] as const,
  lists: () => [...coursesKeys.all, 'list'] as const,
  list: (params?: ListParams) => [...coursesKeys.lists(), { params }] as const,
  details: () => [...coursesKeys.all, 'detail'] as const,
  detail: (id: Id) => [...coursesKeys.details(), id] as const,
}

const fetchCourses = async (params?: ListParams): Promise<Course[]> => {
  const res = await api.get('/courses', { params })
  return res.data
}

const fetchCourse = async (id: Id): Promise<Course> => {
  const res = await api.get(`/courses/${id}`)
  return res.data
}

const createCourse = async (data: CreateCourseInput): Promise<Course> => {
  const res = await api.post('/courses', data)
  return res.data
}

const updateCourse = async (id: Id, data: UpdateCourseInput): Promise<Course> => {
  const res = await api.put(`/courses/${id}`, data)
  return res.data
}

const deleteCourse = async (id: Id): Promise<void> => {
  await api.delete(`/courses/${id}`)
}

export function useCourses(params?: ListParams, enabled = true) {
  return useQuery({
    queryKey: coursesKeys.list(params),
    queryFn: () => fetchCourses(params),
    enabled,
  })
}

export function useCourse(id?: Id, enabled = true) {
  return useQuery({
    queryKey: id != null ? coursesKeys.detail(id) : coursesKeys.detail('unknown'),
    queryFn: () => fetchCourse(id as Id),
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
    mutationFn: ({ id, data }: { id: Id; data: UpdateCourseInput }) => updateCourse(id, data),
    onSuccess: (_course, vars) => {
      qc.invalidateQueries({ queryKey: coursesKeys.detail(vars.id) }).then()
      qc.invalidateQueries({ queryKey: coursesKeys.lists() }).then()
    },
  })
}

export function useDeleteCourse() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: Id) => deleteCourse(id),
    onSuccess: (_void, id) => {
      qc.invalidateQueries({ queryKey: coursesKeys.detail(id) }).then()
      qc.invalidateQueries({ queryKey: coursesKeys.lists() }).then()
    },
  })
}
