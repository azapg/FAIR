import { useQuery } from '@tanstack/react-query'

import api from '@/lib/api'
import type {
  GradebookCategory,
  GradebookCategoryTotal,
  GradebookCourseTotal,
} from '@/hooks/use-lms'

export type StudentGradeItem = {
  gradeItemId: string
  categoryId?: string | null
  title?: string | null
  maxPoints?: number | null
  status: 'graded' | 'excused' | 'missing' | 'unreleased'
  pointsEarned?: number | null
  releasedAt?: string | null
  note?: string | null
  assignmentId?: string | null
  submissionId?: string | null
  contributionPercentagePoints?: number | null
}

export type StudentCourseGrades = {
  courseId: string
  courseName: string
  term?: string | null
  total: GradebookCourseTotal
  currentGradeLabel: string
  finalGradeAvailable: boolean
  categories: GradebookCategory[]
  categoryTotals: GradebookCategoryTotal[]
  items: StudentGradeItem[]
}

export type StudentDashboardWorkItem = {
  assignmentId: string
  courseId: string
  courseName: string
  title: string
  deadline?: string | null
  timezoneName: string
  state: 'upcoming' | 'overdue' | 'submitted'
  submissionId?: string | null
}

export type StudentReturnedFeedback = {
  assignmentId: string
  submissionId: string
  courseId: string
  courseName: string
  assignmentTitle: string
  pointsEarned?: number | null
  maxPoints?: number | null
  feedbackAvailable: boolean
  returnedAt: string
  link: string
}

export type StudentCourseActivity = {
  id: string
  courseId: string
  courseName: string
  kind: 'announcement' | 'material' | 'assignment'
  title: string
  occurredAt: string
  link: string
}

export type StudentCourseProgress = {
  courseId: string
  courseName: string
  term?: string | null
  completedItems: number
  trackedItems: number
  completionPercentage?: number | null
  currentGrade?: number | null
  pointsEarned: number
  pointsPossible: number
  gradeIsProvisional: boolean
}

export type StudentDashboardSourceStatus = {
  source: 'work' | 'feedback' | 'activity' | 'progress'
  available: boolean
  message?: string | null
}

export type StudentDashboard = {
  generatedAt: string
  upcomingWork: StudentDashboardWorkItem[]
  overdueWork: StudentDashboardWorkItem[]
  returnedFeedback: StudentReturnedFeedback[]
  recentActivity: StudentCourseActivity[]
  courseProgress: StudentCourseProgress[]
  sources: StudentDashboardSourceStatus[]
}

export function useStudentDashboard() {
  return useQuery({
    queryKey: ['lms', 'student-dashboard'],
    queryFn: async (): Promise<StudentDashboard> =>
      (await api.get('/lms/student/dashboard')).data,
  })
}

export function useStudentCourseGrades(courseId?: string, enabled = true) {
  return useQuery({
    queryKey: ['lms', 'student-grades', courseId],
    queryFn: async (): Promise<StudentCourseGrades> =>
      (await api.get(`/lms/courses/${courseId}/grades`)).data,
    enabled: enabled && Boolean(courseId),
  })
}
