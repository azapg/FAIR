import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'

import api from '@/lib/api'


export type QuestionKind = 'single_choice' | 'true_false'
export type QuizStatus = 'draft' | 'published' | 'closed'
export type QuizReleasePolicy = 'immediate' | 'manual'
export type QuizAttemptStatus = 'in_progress' | 'submitted' | 'released'

export type QuestionOption = { id: string; text: string }

export type QuestionVersion = {
  id: string
  questionId: string
  versionNumber: number
  kind: QuestionKind
  prompt: string
  options: QuestionOption[]
  correctOptionId: string
  defaultPoints: number
  explanation?: string | null
  createdAt: string
}

export type Question = {
  id: string
  bankId: string
  title: string
  createdAt: string
  updatedAt: string
  versions: QuestionVersion[]
}

export type QuestionBank = {
  id: string
  courseId: string
  name: string
  description?: string | null
  createdAt: string
  updatedAt: string
  questions: Question[]
}

export type Quiz = {
  id: string
  courseId: string
  courseItemId: string
  title: string
  instructions?: string | null
  status: QuizStatus
  releasePolicy: QuizReleasePolicy
  attemptLimit: number
  opensAt?: string | null
  closesAt?: string | null
  publishedAt?: string | null
  closedAt?: string | null
  questionCount: number
  maxPoints: number
  createdAt: string
  updatedAt: string
}

export type QuizAuthoring = Quiz & {
  questions: Array<{
    id: string
    position: number
    points: number
    version: QuestionVersion
  }>
}

export type AttemptQuestion = {
  id: string
  questionVersionId: string
  position: number
  kind: QuestionKind
  prompt: string
  options: QuestionOption[]
  points: number
  selectedOptionId?: string | null
  isCorrect?: boolean | null
  pointsAwarded?: number | null
}

export type QuizAttempt = {
  id: string
  quizId: string
  userId: string
  attemptNumber: number
  status: QuizAttemptStatus
  maxPoints: number
  earnedPoints?: number | null
  startedAt: string
  submittedAt?: string | null
  releasedAt?: string | null
  questions: AttemptQuestion[]
}

export type QuestionInput = {
  title: string
  kind: QuestionKind
  prompt: string
  options: string[]
  correctOptionIndex: number
  defaultPoints: number
  explanation?: string | null
}

export type QuizInput = {
  sectionId: string
  title: string
  instructions?: string | null
  attemptLimit: number
  releasePolicy: QuizReleasePolicy
}

export const quizKeys = {
  all: ['quizzes'] as const,
  course: (courseId: string) => [...quizKeys.all, courseId] as const,
  detail: (courseId: string, quizId: string) => [...quizKeys.course(courseId), quizId] as const,
  authoring: (courseId: string, quizId: string) => [...quizKeys.detail(courseId, quizId), 'authoring'] as const,
  attempts: (
    courseId: string,
    quizId: string,
    viewerId: string,
    scope: 'staff' | 'learner',
  ) => [...quizKeys.detail(courseId, quizId), 'attempts', scope, viewerId] as const,
  banks: (courseId: string) => [...quizKeys.course(courseId), 'question-banks'] as const,
}

function useInvalidateQuiz(courseId: string, quizId?: string) {
  const queryClient = useQueryClient()
  return async () => {
    await queryClient.invalidateQueries({ queryKey: quizKeys.course(courseId) })
    if (quizId) await queryClient.invalidateQueries({ queryKey: quizKeys.detail(courseId, quizId) })
  }
}

export function useQuestionBanks(courseId: string, enabled = true) {
  return useQuery({
    queryKey: quizKeys.banks(courseId),
    queryFn: async (): Promise<QuestionBank[]> =>
      (await api.get(`/lms/courses/${courseId}/question-banks`)).data,
    enabled: Boolean(courseId) && enabled,
  })
}

export function useCreateQuestionBank(courseId: string) {
  const invalidate = useInvalidateQuiz(courseId)
  return useMutation({
    mutationFn: async (input: { name: string; description?: string | null }): Promise<QuestionBank> =>
      (await api.post(`/lms/courses/${courseId}/question-banks`, input)).data,
    onSuccess: invalidate,
    onError: (error: Error) => toast.error('Failed to create question bank', { description: error.message }),
  })
}

export function useCreateQuestion(courseId: string) {
  const invalidate = useInvalidateQuiz(courseId)
  return useMutation({
    mutationFn: async ({ bankId, input }: { bankId: string; input: QuestionInput }): Promise<Question> =>
      (await api.post(`/lms/courses/${courseId}/question-banks/${bankId}/questions`, input)).data,
    onSuccess: invalidate,
    onError: (error: Error) => toast.error('Failed to create question', { description: error.message }),
  })
}

export function useCreateQuiz(courseId: string) {
  const invalidate = useInvalidateQuiz(courseId)
  return useMutation({
    mutationFn: async (input: QuizInput): Promise<QuizAuthoring> =>
      (await api.post(`/lms/courses/${courseId}/quizzes`, input)).data,
    onSuccess: invalidate,
    onError: (error: Error) => toast.error('Failed to create quiz', { description: error.message }),
  })
}

export function useAddQuizQuestion(courseId: string) {
  const invalidate = useInvalidateQuiz(courseId)
  return useMutation({
    mutationFn: async ({ quizId, questionVersionId, points }: { quizId: string; questionVersionId: string; points?: number }): Promise<QuizAuthoring> =>
      (await api.post(`/lms/courses/${courseId}/quizzes/${quizId}/questions`, { questionVersionId, points })).data,
    onSuccess: invalidate,
    onError: (error: Error) => toast.error('Failed to add quiz question', { description: error.message }),
  })
}

export function useQuiz(courseId: string, quizId: string, enabled = true) {
  return useQuery({
    queryKey: quizKeys.detail(courseId, quizId),
    queryFn: async (): Promise<Quiz> =>
      (await api.get(`/lms/courses/${courseId}/quizzes/${quizId}`)).data,
    enabled: Boolean(courseId && quizId) && enabled,
  })
}

export function useQuizAuthoring(courseId: string, quizId: string, enabled = true) {
  return useQuery({
    queryKey: quizKeys.authoring(courseId, quizId),
    queryFn: async (): Promise<QuizAuthoring> =>
      (await api.get(`/lms/courses/${courseId}/quizzes/${quizId}/authoring`)).data,
    enabled: Boolean(courseId && quizId) && enabled,
  })
}

export function useQuizAttempts(
  courseId: string,
  quizId: string,
  viewerId: string,
  scope: 'staff' | 'learner',
  enabled = true,
) {
  return useQuery({
    queryKey: quizKeys.attempts(courseId, quizId, viewerId, scope),
    queryFn: async (): Promise<QuizAttempt[]> =>
      (await api.get(`/lms/courses/${courseId}/quizzes/${quizId}/attempts`)).data,
    enabled: Boolean(courseId && quizId && viewerId) && enabled,
  })
}

function useQuizAction(
  courseId: string,
  quizId: string,
  action: 'publish' | 'close',
  successMessage: string,
) {
  const invalidate = useInvalidateQuiz(courseId, quizId)
  return useMutation({
    mutationFn: async (): Promise<QuizAuthoring> =>
      (await api.post(`/lms/courses/${courseId}/quizzes/${quizId}/${action}`)).data,
    onSuccess: async () => {
      await invalidate()
      toast.success(successMessage)
    },
    onError: (error: Error) => toast.error(`Failed to ${action} quiz`, { description: error.message }),
  })
}

export function usePublishQuiz(courseId: string, quizId: string) {
  return useQuizAction(courseId, quizId, 'publish', 'Quiz published')
}

export function useCloseQuiz(courseId: string, quizId: string) {
  return useQuizAction(courseId, quizId, 'close', 'Quiz closed')
}

export function useStartQuizAttempt(courseId: string, quizId: string) {
  const invalidate = useInvalidateQuiz(courseId, quizId)
  return useMutation({
    mutationFn: async (): Promise<QuizAttempt> =>
      (await api.post(`/lms/courses/${courseId}/quizzes/${quizId}/attempts`)).data,
    onSuccess: invalidate,
    onError: (error: Error) => toast.error('Could not start quiz', { description: error.message }),
  })
}

export function useSaveQuizAnswer(courseId: string, quizId: string) {
  const invalidate = useInvalidateQuiz(courseId, quizId)
  return useMutation({
    mutationFn: async ({ attemptId, questionId, selectedOptionId }: { attemptId: string; questionId: string; selectedOptionId: string }): Promise<QuizAttempt> =>
      (await api.put(
        `/lms/courses/${courseId}/quizzes/${quizId}/attempts/${attemptId}/answers/${questionId}`,
        { selectedOptionId },
      )).data,
    onSuccess: invalidate,
    onError: (error: Error) => toast.error('Answer was not saved', { description: error.message }),
  })
}

export function useSubmitQuizAttempt(courseId: string, quizId: string) {
  const invalidate = useInvalidateQuiz(courseId, quizId)
  return useMutation({
    mutationFn: async (attemptId: string): Promise<QuizAttempt> =>
      (await api.post(`/lms/courses/${courseId}/quizzes/${quizId}/attempts/${attemptId}/submit`)).data,
    onSuccess: async () => {
      await invalidate()
      toast.success('Quiz submitted')
    },
    onError: (error: Error) => toast.error('Could not submit quiz', { description: error.message }),
  })
}

export function useReleaseQuizAttempt(courseId: string, quizId: string) {
  const invalidate = useInvalidateQuiz(courseId, quizId)
  return useMutation({
    mutationFn: async (attemptId: string): Promise<QuizAttempt> =>
      (await api.post(`/lms/courses/${courseId}/quizzes/${quizId}/attempts/${attemptId}/release`)).data,
    onSuccess: async () => {
      await invalidate()
      toast.success('Quiz score released')
    },
    onError: (error: Error) => toast.error('Could not release score', { description: error.message }),
  })
}
