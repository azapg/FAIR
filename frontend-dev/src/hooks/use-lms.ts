import { useQuery } from '@tanstack/react-query'
import api from '@/lib/api'

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
}

export type CourseGradebook = {
  courseId: string
  assignments: GradebookAssignment[]
  rows: GradebookRow[]
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
