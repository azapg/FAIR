import { useEffect, useMemo, useState } from 'react'
import { CheckCircle2, CircleHelp, LockKeyhole } from 'lucide-react'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { useAuth } from '@/contexts/auth-context'
import {
  useCloseQuiz,
  usePublishQuiz,
  useQuiz,
  useQuizAttempts,
  useQuizAuthoring,
  useReleaseQuizAttempt,
  useSaveQuizAnswer,
  useStartQuizAttempt,
  useSubmitQuizAttempt,
} from '@/hooks/use-quizzes'
import type { Quiz, QuizAttempt, QuizAuthoring } from '@/hooks/use-quizzes'


function isQuizAuthoring(quiz: Quiz | QuizAuthoring): quiz is QuizAuthoring {
  return 'questions' in quiz && Array.isArray(quiz.questions)
}


function AttemptForm({
  courseId,
  quizId,
  attempt,
  isArchived,
}: {
  courseId: string
  quizId: string
  attempt: QuizAttempt
  isArchived: boolean
}) {
  const saveAnswer = useSaveQuizAnswer(courseId, quizId)
  const submitAttempt = useSubmitQuizAttempt(courseId, quizId)
  const [selections, setSelections] = useState<Record<string, string>>({})

  useEffect(() => {
    setSelections(Object.fromEntries(
      attempt.questions
        .filter((question) => question.selectedOptionId)
        .map((question) => [question.id, question.selectedOptionId as string]),
    ))
  }, [attempt])

  if (attempt.status === 'submitted') {
    return (
      <div className="rounded-md border bg-muted/30 p-3 text-sm">
        Submitted. Your score is waiting for staff release.
      </div>
    )
  }
  if (attempt.status === 'released') {
    return (
      <div className="space-y-2 rounded-md border bg-muted/30 p-3 text-sm">
        <div className="flex items-center gap-2 font-medium">
          <CheckCircle2 className="h-4 w-4 text-emerald-600" />
          Score: {attempt.earnedPoints ?? 0} / {attempt.maxPoints}
        </div>
        {attempt.questions.map((question) => (
          <p key={question.id} className="text-muted-foreground">
            Question {question.position + 1}: {question.isCorrect ? 'Correct' : 'Incorrect'}
            {' · '}{question.pointsAwarded ?? 0} / {question.points} points
          </p>
        ))}
      </div>
    )
  }

  const answer = async (questionId: string, selectedOptionId: string) => {
    setSelections((current) => ({ ...current, [questionId]: selectedOptionId }))
    await saveAnswer.mutateAsync({ attemptId: attempt.id, questionId, selectedOptionId })
  }
  const answered = Object.keys(selections).length

  return (
    <div className="space-y-4">
      {attempt.questions.map((question) => (
        <fieldset key={question.id} className="space-y-2 rounded-md border p-3">
          <legend className="px-1 text-sm font-medium">
            {question.position + 1}. {question.prompt} ({question.points} points)
          </legend>
          {question.options.map((option) => (
            <label key={option.id} className="flex cursor-pointer items-start gap-2 rounded px-2 py-1.5 text-sm hover:bg-muted/50">
              <input
                type="radio"
                name={`question-${question.id}`}
                value={option.id}
                checked={selections[question.id] === option.id}
                disabled={isArchived || saveAnswer.isPending}
                onChange={() => answer(question.id, option.id)}
              />
              <span>{option.text}</span>
            </label>
          ))}
        </fieldset>
      ))}
      <div className="flex flex-wrap items-center justify-between gap-2">
        <span className="text-xs text-muted-foreground">{answered} of {attempt.questions.length} answered · answers save automatically</span>
        <Button
          size="sm"
          disabled={isArchived || submitAttempt.isPending || saveAnswer.isPending}
          onClick={() => submitAttempt.mutate(attempt.id)}
        >
          {submitAttempt.isPending ? 'Submitting…' : 'Submit quiz'}
        </Button>
      </div>
    </div>
  )
}


export function QuizCard({
  courseId,
  quizId,
  canManage,
  isArchived,
}: {
  courseId: string
  quizId: string
  canManage: boolean
  isArchived: boolean
}) {
  const { user } = useAuth()
  const learnerQuiz = useQuiz(courseId, quizId, !canManage)
  const authoredQuiz = useQuizAuthoring(courseId, quizId, canManage)
  const attemptsQuery = useQuizAttempts(
    courseId,
    quizId,
    user?.id ?? '',
    canManage ? 'staff' : 'learner',
    Boolean(user?.id),
  )
  const quiz = canManage ? authoredQuiz.data : learnerQuiz.data
  const attempts = attemptsQuery.data ?? []
  const latestAttempt = useMemo(
    () => attempts.length ? attempts[attempts.length - 1] : undefined,
    [attempts],
  )
  const publishQuiz = usePublishQuiz(courseId, quizId)
  const closeQuiz = useCloseQuiz(courseId, quizId)
  const startAttempt = useStartQuizAttempt(courseId, quizId)
  const releaseAttempt = useReleaseQuizAttempt(courseId, quizId)
  const canStartNextAttempt = Boolean(
    !canManage
      && quiz?.status === 'published'
      && latestAttempt
      && latestAttempt.status !== 'in_progress'
      && attempts.length < quiz.attemptLimit,
  )

  if (learnerQuiz.isLoading || authoredQuiz.isLoading || attemptsQuery.isLoading) {
    return <div className="text-sm text-muted-foreground">Loading quiz…</div>
  }
  if (!quiz) return <div className="text-sm text-muted-foreground">Quiz is unavailable.</div>

  return (
    <div className="space-y-3 rounded-md border bg-card p-4">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <CircleHelp className="h-4 w-4 text-primary" />
            <h4 className="font-semibold">{quiz.title}</h4>
            <Badge variant="outline">{quiz.status}</Badge>
          </div>
          {quiz.instructions && <p className="mt-1 text-sm text-muted-foreground">{quiz.instructions}</p>}
          <p className="mt-1 text-xs text-muted-foreground">
            {quiz.questionCount} {quiz.questionCount === 1 ? 'question' : 'questions'} · {quiz.maxPoints} points · {quiz.attemptLimit} {quiz.attemptLimit === 1 ? 'attempt' : 'attempts'}
          </p>
        </div>
        {canManage && !isArchived && (
          <div className="flex gap-2">
            {quiz.status === 'draft' && (
              <Button size="sm" disabled={publishQuiz.isPending} onClick={() => publishQuiz.mutate()}>
                {publishQuiz.isPending ? 'Publishing…' : 'Publish'}
              </Button>
            )}
            {quiz.status === 'published' && (
              <Button size="sm" variant="outline" disabled={closeQuiz.isPending} onClick={() => closeQuiz.mutate()}>
                Close attempts
              </Button>
            )}
          </div>
        )}
      </div>

      {canManage && isQuizAuthoring(quiz) && (
        <div className="space-y-2">
          {quiz.questions.map((question) => (
            <div key={question.id} className="rounded-md bg-muted/35 p-3 text-sm">
              <p className="font-medium">{question.position + 1}. {question.version.prompt}</p>
              <div className="mt-1 flex flex-wrap gap-1">
                {question.version.options.map((option) => (
                  <Badge key={option.id} variant={option.id === question.version.correctOptionId ? 'default' : 'secondary'}>
                    {option.text}{option.id === question.version.correctOptionId ? ' · correct' : ''}
                  </Badge>
                ))}
              </div>
            </div>
          ))}
          {quiz.questions.length === 0 && <p className="text-sm text-muted-foreground">No questions have been added.</p>}
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <LockKeyhole className="h-3.5 w-3.5" /> Answer keys are only returned by the staff authoring endpoint.
          </div>
        </div>
      )}

      {!canManage && (
        <>
          {!latestAttempt && quiz.status === 'published' && (
            <Button size="sm" disabled={isArchived || startAttempt.isPending} onClick={() => startAttempt.mutate()}>
              {startAttempt.isPending ? 'Starting…' : 'Start quiz'}
            </Button>
          )}
          {!latestAttempt && quiz.status === 'closed' && (
            <p className="text-sm text-muted-foreground">This quiz is closed.</p>
          )}
          {latestAttempt && (
            <AttemptForm courseId={courseId} quizId={quizId} attempt={latestAttempt} isArchived={isArchived} />
          )}
          {canStartNextAttempt && (
            <Button size="sm" disabled={isArchived || startAttempt.isPending} onClick={() => startAttempt.mutate()}>
              {startAttempt.isPending ? 'Starting…' : 'Start next attempt'}
            </Button>
          )}
        </>
      )}

      {canManage && (
        <div className="space-y-2 border-t pt-3">
          <p className="text-sm font-medium">Attempts</p>
          {attempts.map((attempt) => (
            <div key={attempt.id} className="flex flex-wrap items-center justify-between gap-2 rounded-md bg-muted/30 px-3 py-2 text-sm">
              <span>Learner {attempt.userId.slice(0, 8)} · attempt {attempt.attemptNumber} · {attempt.status}</span>
              <span className="flex items-center gap-2">
                {attempt.earnedPoints != null && <span>{attempt.earnedPoints} / {attempt.maxPoints}</span>}
                {attempt.status === 'submitted' && !isArchived && (
                  <Button size="sm" variant="outline" disabled={releaseAttempt.isPending} onClick={() => releaseAttempt.mutate(attempt.id)}>
                    Release score
                  </Button>
                )}
              </span>
            </div>
          ))}
          {attempts.length === 0 && <p className="text-sm text-muted-foreground">No attempts yet.</p>}
        </div>
      )}
    </div>
  )
}
