import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'


const mocks = vi.hoisted(() => ({
  mode: 'staff' as 'staff' | 'learner',
  save: vi.fn(),
  submit: vi.fn(),
  release: vi.fn(),
  publish: vi.fn(),
  close: vi.fn(),
  start: vi.fn(),
  attemptLimit: 1,
  attempts: null as Array<Record<string, unknown>> | null,
  attemptHook: vi.fn(),
}))

const quiz = {
  id: 'quiz-1',
  courseId: 'course-1',
  courseItemId: 'item-1',
  title: 'Capital check',
  instructions: 'Choose the best answer.',
  status: 'published',
  releasePolicy: 'manual',
  attemptLimit: 1,
  questionCount: 1,
  maxPoints: 4,
  createdAt: '2026-08-12T00:00:00Z',
  updatedAt: '2026-08-12T00:00:00Z',
}

const version = {
  id: 'version-1',
  questionId: 'question-1',
  versionNumber: 1,
  kind: 'single_choice',
  prompt: 'What is the capital of Panama?',
  options: [
    { id: 'panama-city', text: 'Panama City' },
    { id: 'colon', text: 'Colon' },
  ],
  correctOptionId: 'panama-city',
  defaultPoints: 4,
  createdAt: '2026-08-12T00:00:00Z',
}

const inProgressAttempt = {
  id: 'attempt-1',
  quizId: 'quiz-1',
  userId: 'student-1',
  attemptNumber: 1,
  status: 'in_progress',
  maxPoints: 4,
  startedAt: '2026-08-12T00:00:00Z',
  questions: [{
    id: 'attempt-question-1',
    questionVersionId: 'version-1',
    position: 0,
    kind: 'single_choice',
    prompt: version.prompt,
    options: version.options,
    points: 4,
  }],
}

vi.mock('@/hooks/use-quizzes', () => ({
  useQuiz: () => ({
    data: mocks.mode === 'learner'
      ? { ...quiz, attemptLimit: mocks.attemptLimit }
      : undefined,
    isLoading: false,
  }),
  useQuizAuthoring: () => ({
    data: mocks.mode === 'staff' ? {
      ...quiz,
      attemptLimit: mocks.attemptLimit,
      questions: [{ id: 'link-1', position: 0, points: 4, version }],
    } : undefined,
    isLoading: false,
  }),
  useQuizAttempts: (...args: unknown[]) => {
    mocks.attemptHook(...args)
    return {
      data: mocks.attempts ?? (mocks.mode === 'staff'
        ? [{ ...inProgressAttempt, status: 'submitted', earnedPoints: 4, submittedAt: '2026-08-12T00:01:00Z' }]
        : [inProgressAttempt]),
      isLoading: false,
    }
  },
  usePublishQuiz: () => ({ mutate: mocks.publish, isPending: false }),
  useCloseQuiz: () => ({ mutate: mocks.close, isPending: false }),
  useStartQuizAttempt: () => ({ mutate: mocks.start, isPending: false }),
  useSaveQuizAnswer: () => ({ mutateAsync: mocks.save, isPending: false }),
  useSubmitQuizAttempt: () => ({ mutate: mocks.submit, isPending: false }),
  useReleaseQuizAttempt: () => ({ mutate: mocks.release, isPending: false }),
}))

vi.mock('@/contexts/auth-context', () => ({
  useAuth: () => ({
    user: { id: mocks.mode === 'staff' ? 'staff-1' : 'student-1' },
  }),
}))

import { QuizCard } from './quiz-card'


describe('QuizCard', () => {
  afterEach(cleanup)

  beforeEach(() => {
    vi.clearAllMocks()
    mocks.save.mockResolvedValue(inProgressAttempt)
    mocks.attemptLimit = 1
    mocks.attempts = null
  })

  it('shows answer keys and release controls only in the staff workspace', () => {
    mocks.mode = 'staff'
    render(<QuizCard courseId="course-1" quizId="quiz-1" canManage isArchived={false} />)

    expect(screen.getByText('Panama City · correct')).toBeInTheDocument()
    expect(screen.getByText(/Answer keys are only returned/)).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Release score' }))
    expect(mocks.release).toHaveBeenCalledWith('attempt-1')
  })

  it('autosaves learner choices without rendering the protected key', () => {
    mocks.mode = 'learner'
    render(<QuizCard courseId="course-1" quizId="quiz-1" canManage={false} isArchived={false} />)

    expect(screen.queryByText(/· correct/)).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole('radio', { name: 'Panama City' }))
    expect(mocks.save).toHaveBeenCalledWith({
      attemptId: 'attempt-1',
      questionId: 'attempt-question-1',
      selectedOptionId: 'panama-city',
    })
    fireEvent.click(screen.getByRole('button', { name: 'Submit quiz' }))
    expect(mocks.submit).toHaveBeenCalledWith('attempt-1')
  })

  it('disables learner mutation controls for archived courses', () => {
    mocks.mode = 'learner'
    render(<QuizCard courseId="course-1" quizId="quiz-1" canManage={false} isArchived />)

    expect(screen.getByRole('radio', { name: 'Panama City' })).toBeDisabled()
    expect(screen.getByRole('button', { name: 'Submit quiz' })).toBeDisabled()
  })

  it('offers the next attempt only below the configured limit', () => {
    mocks.mode = 'learner'
    mocks.attemptLimit = 2
    mocks.attempts = [{
      ...inProgressAttempt,
      status: 'released',
      earnedPoints: 4,
      submittedAt: '2026-08-12T00:01:00Z',
      releasedAt: '2026-08-12T00:02:00Z',
    }]
    render(<QuizCard courseId="course-1" quizId="quiz-1" canManage={false} isArchived={false} />)

    fireEvent.click(screen.getByRole('button', { name: 'Start next attempt' }))
    expect(mocks.start).toHaveBeenCalledTimes(1)
    expect(mocks.attemptHook).toHaveBeenCalledWith(
      'course-1',
      'quiz-1',
      'student-1',
      'learner',
      true,
    )
  })
})
