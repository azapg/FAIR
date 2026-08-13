import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'

import api from '@/lib/api'


export type CourseContentVisibility = 'draft' | 'published' | 'hidden'
export type CourseItemKind = 'heading' | 'page' | 'link' | 'file' | 'assignment'

export type CourseItem = {
  id: string
  courseId: string
  sectionId: string
  title: string
  position: number
  kind: CourseItemKind
  visibility: CourseContentVisibility
  resourceType?: string | null
  resourceId?: string | null
  payloadSchemaUri?: string | null
  payload: Record<string, unknown>
  createdAt: string
  updatedAt: string
}

export type CourseSection = {
  id: string
  courseId: string
  title: string
  summary?: string | null
  position: number
  visibility: CourseContentVisibility
  createdAt: string
  updatedAt: string
  items: CourseItem[]
}

export type CourseContent = {
  courseId: string
  canManage: boolean
  sections: CourseSection[]
}

export type CreateSectionInput = {
  title: string
  summary?: string | null
  visibility: CourseContentVisibility
}

export type UpdateSectionInput = Partial<CreateSectionInput>

export type CreateItemInput = {
  title: string
  kind: CourseItemKind
  visibility: CourseContentVisibility
  resourceId?: string | null
  payload?: Record<string, unknown>
}

export type UpdateItemInput = Partial<Pick<CreateItemInput, 'title' | 'visibility' | 'payload'>>

export const courseContentKeys = {
  all: ['course-content'] as const,
  course: (courseId: string) => [...courseContentKeys.all, courseId] as const,
}

async function fetchCourseContent(courseId: string): Promise<CourseContent> {
  return (await api.get(`/lms/courses/${courseId}/content`)).data
}

function useInvalidateCourseContent(courseId: string) {
  const queryClient = useQueryClient()
  return () => queryClient.invalidateQueries({ queryKey: courseContentKeys.course(courseId) })
}

export function useCourseContent(courseId?: string) {
  return useQuery({
    queryKey: courseContentKeys.course(courseId ?? 'unknown'),
    queryFn: () => fetchCourseContent(courseId as string),
    enabled: Boolean(courseId),
  })
}

export function useCreateCourseSection(courseId: string) {
  const invalidate = useInvalidateCourseContent(courseId)
  return useMutation({
    mutationFn: async (data: CreateSectionInput): Promise<CourseSection> =>
      (await api.post(`/lms/courses/${courseId}/sections`, data)).data,
    onSuccess: () => {
      invalidate()
      toast.success('Section created')
    },
    onError: (error: Error) => toast.error('Failed to create section', { description: error.message }),
  })
}

export function useUpdateCourseSection(courseId: string) {
  const invalidate = useInvalidateCourseContent(courseId)
  return useMutation({
    mutationFn: async ({ id, data }: { id: string; data: UpdateSectionInput }): Promise<CourseSection> =>
      (await api.patch(`/lms/courses/${courseId}/sections/${id}`, data)).data,
    onSuccess: () => {
      invalidate()
      toast.success('Section updated')
    },
    onError: (error: Error) => toast.error('Failed to update section', { description: error.message }),
  })
}

export function useDeleteCourseSection(courseId: string) {
  const invalidate = useInvalidateCourseContent(courseId)
  return useMutation({
    mutationFn: async (id: string): Promise<void> => {
      await api.delete(`/lms/courses/${courseId}/sections/${id}`)
    },
    onSuccess: () => {
      invalidate()
      toast.success('Section deleted')
    },
    onError: (error: Error) => toast.error('Failed to delete section', { description: error.message }),
  })
}

export function useReorderCourseSections(courseId: string) {
  const invalidate = useInvalidateCourseContent(courseId)
  return useMutation({
    mutationFn: async (orderedIds: string[]): Promise<CourseSection[]> =>
      (await api.put(`/lms/courses/${courseId}/sections/order`, { orderedIds })).data,
    onSuccess: invalidate,
    onError: (error: Error) => toast.error('Failed to reorder sections', { description: error.message }),
  })
}

export function useCreateCourseItem(courseId: string) {
  const invalidate = useInvalidateCourseContent(courseId)
  return useMutation({
    mutationFn: async ({ sectionId, data }: { sectionId: string; data: CreateItemInput }): Promise<CourseItem> =>
      (await api.post(`/lms/courses/${courseId}/sections/${sectionId}/items`, data)).data,
    onSuccess: () => {
      invalidate()
      toast.success('Content item created')
    },
    onError: (error: Error) => toast.error('Failed to create content item', { description: error.message }),
  })
}

export function useUpdateCourseItem(courseId: string) {
  const invalidate = useInvalidateCourseContent(courseId)
  return useMutation({
    mutationFn: async ({ id, data }: { id: string; data: UpdateItemInput }): Promise<CourseItem> =>
      (await api.patch(`/lms/courses/${courseId}/items/${id}`, data)).data,
    onSuccess: () => {
      invalidate()
      toast.success('Content item updated')
    },
    onError: (error: Error) => toast.error('Failed to update content item', { description: error.message }),
  })
}

export function useDeleteCourseItem(courseId: string) {
  const invalidate = useInvalidateCourseContent(courseId)
  return useMutation({
    mutationFn: async (id: string): Promise<void> => {
      await api.delete(`/lms/courses/${courseId}/items/${id}`)
    },
    onSuccess: () => {
      invalidate()
      toast.success('Content item deleted')
    },
    onError: (error: Error) => toast.error('Failed to delete content item', { description: error.message }),
  })
}

export function useReorderCourseItems(courseId: string) {
  const invalidate = useInvalidateCourseContent(courseId)
  return useMutation({
    mutationFn: async ({ sectionId, orderedIds }: { sectionId: string; orderedIds: string[] }): Promise<CourseItem[]> =>
      (await api.put(`/lms/courses/${courseId}/sections/${sectionId}/items/order`, { orderedIds })).data,
    onSuccess: invalidate,
    onError: (error: Error) => toast.error('Failed to reorder content items', { description: error.message }),
  })
}
