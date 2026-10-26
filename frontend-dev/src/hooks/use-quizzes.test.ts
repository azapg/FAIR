import { describe, expect, it } from 'vitest'

import { quizKeys } from './use-quizzes'


describe('quiz attempt cache keys', () => {
  it('isolates private attempts by viewer and authorization scope', () => {
    const staff = quizKeys.attempts('course-1', 'quiz-1', 'staff-1', 'staff')
    const firstLearner = quizKeys.attempts(
      'course-1',
      'quiz-1',
      'student-1',
      'learner',
    )
    const secondLearner = quizKeys.attempts(
      'course-1',
      'quiz-1',
      'student-2',
      'learner',
    )

    expect(staff).not.toEqual(firstLearner)
    expect(firstLearner).not.toEqual(secondLearner)
  })
})
