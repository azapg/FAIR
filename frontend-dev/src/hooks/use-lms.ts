import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import api from '@/lib/api'
import { toast } from 'sonner'

export type GradebookAssignment = {
  id: string
  title: string
  deadline?: string | null
  maxGrade?: Record<string, unknown> | null
}

export type GradebookCell = {
  assignmentId: string
  state: 'missing' | 'submitted' | 'returned' | 'excused'
  submissionId?: string | null
  score?: number | null
  submittedAt?: string | null
  isLate: boolean
  attemptCount: number
}

export type GradebookRow = {
  userId: string
  name: string
  email: string
  cells: GradebookCell[]
  itemCells: GradebookEntryCell[]
  categoryTotals: GradebookCategoryTotal[]
  courseTotal?: GradebookCourseTotal | null
}

export type GradebookCategory = {
  id: string
  name: string
  description?: string | null
  position: number
  weight?: number | null
  aggregationStrategy: string
  isDefault: boolean
}

export type GradebookItem = {
  id: string
  categoryId?: string | null
  title: string
  description?: string | null
  position: number
  maxPoints: number
  sourceType?: string | null
  sourceId?: string | null
  isManual: boolean
}

export type GradebookEntryCell = {
  gradeItemId: string
  status: 'graded' | 'excused' | 'missing' | 'absent'
  releaseState: 'released' | 'unreleased' | 'absent'
  pointsEarned?: number | null
  sourceType?: string | null
  sourceId?: string | null
  releasedAt?: string | null
  note?: string | null
}

export type GradebookTotal = {
  pointsEarned: number
  pointsPossible: number
  percentage?: number | null
  provisional: boolean
  gradedItemCount: number
  excusedItemCount: number
  missingEntryCount: number
  reasons: string[]
}

export type GradebookCategoryTotal = GradebookTotal & {
  categoryId: string
  weight?: number | null
}

export type GradebookCourseTotal = GradebookTotal & {
  calculation: 'points' | 'category_weighted'
  configuredWeightTotal?: number | null
}

export type CourseGradebook = {
  courseId: string
  assignments: GradebookAssignment[]
  rows: GradebookRow[]
  categories: GradebookCategory[]
  items: GradebookItem[]
}

export type CreateGradebookCategory = {
  name: string
  description?: string | null
  weight?: number | null
}

export type UpdateGradebookCategory = {
  name?: string
  description?: string | null
  position?: number
  weight?: number | null
}

export type CreateGradebookItem = {
  categoryId?: string | null
  title: string
  description?: string | null
  maxPoints: number
}

export type UpsertGradebookEntry = {
  itemId: string
  userId: string
  status: 'graded' | 'excused' | 'missing'
  pointsEarned?: number | null
  note?: string | null
}

export type GradingQueueItem = {
  submissionId: string
  assignmentId: string
  assignmentTitle: string
  userId: string
  studentName: string
  submittedAt?: string | null
  isLate: boolean
  attemptNumber: number
  status: string
}

export type StudentTodoItem = {
  assignmentId: string
  assignmentTitle: string
  courseId: string
  courseName: string
  deadline?: string | null
  state: 'missing' | 'submitted'
  submissionId?: string | null
  attemptCount: number
  isLate: boolean
}

export function useCourseGradebook(courseId?: string) {
  return useQuery({
    queryKey: ['lms', 'gradebook', courseId],
    queryFn: async (): Promise<CourseGradebook> =>
      (await api.get(`/lms/courses/${courseId}/gradebook`)).data,
    enabled: Boolean(courseId),
  })
}

export function useCreateGradebookCategory(courseId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (payload: CreateGradebookCategory) =>
      (await api.post(`/lms/courses/${courseId}/gradebook/categories`, payload)).data,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['lms', 'gradebook', courseId] })
      toast.success('Grade category created')
    },
    onError: (error: Error) =>
      toast.error('Failed to create grade category', { description: error.message }),
  })
}

export function useUpdateGradebookCategory(courseId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async ({ categoryId, ...payload }: UpdateGradebookCategory & { categoryId: string }) =>
      (await api.patch(`/lms/courses/${courseId}/gradebook/categories/${categoryId}`, payload)).data,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['lms', 'gradebook', courseId] })
      toast.success('Grade category updated')
    },
    onError: (error: Error) =>
      toast.error('Failed to update grade category', { description: error.message }),
  })
}

export function useCreateGradebookItem(courseId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (payload: CreateGradebookItem) =>
      (await api.post(`/lms/courses/${courseId}/gradebook/items`, payload)).data,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['lms', 'gradebook', courseId] })
      toast.success('Manual grade item created')
    },
    onError: (error: Error) =>
      toast.error('Failed to create grade item', { description: error.message }),
  })
}

export function useUpsertGradebookEntry(courseId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async ({ itemId, userId, ...payload }: UpsertGradebookEntry) =>
      (
        await api.put(
          `/lms/courses/${courseId}/gradebook/items/${itemId}/entries/${userId}`,
          payload,
        )
      ).data,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['lms', 'gradebook', courseId] })
      toast.success('Grade entry released')
    },
    onError: (error: Error) =>
      toast.error('Failed to release grade entry', { description: error.message }),
  })
}

export function useGradingQueue(courseId?: string) {
  return useQuery({
    queryKey: ['lms', 'grading-queue', courseId],
    queryFn: async (): Promise<GradingQueueItem[]> =>
      (await api.get(`/lms/courses/${courseId}/grading-queue`)).data,
    enabled: Boolean(courseId),
  })
}

export function useStudentTodo() {
  return useQuery({
    queryKey: ['lms', 'todo'],
    queryFn: async (): Promise<StudentTodoItem[]> => (await api.get('/lms/todo')).data,
  })
}
