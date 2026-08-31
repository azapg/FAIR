import { describe, expect, it } from 'vitest'

import type { Course } from './use-courses'
import { hasStaffCourseMembership } from './use-courses'


function course(overrides: Partial<Course>): Course {
  return {
    id: 'course-1',
    name: 'Course',
    iconKey: 'book-open',
    instructorId: 'instructor-1',
    assignmentsCount: 0,
    isEnrollmentEnabled: false,
    isArchived: false,
    ...overrides,
  }
}


describe('hasStaffCourseMembership', () => {
  it('keeps archived owner and assistant memberships out of learner-only navigation', () => {
    expect(
      hasStaffCourseMembership([
        course({ membershipRole: 'student' }),
        course({ id: 'archived', membershipRole: 'owner', isArchived: true }),
      ]),
    ).toBe(true)
    expect(
      hasStaffCourseMembership([
        course({ membershipRole: 'assistant', isArchived: true }),
      ]),
    ).toBe(true)
    expect(hasStaffCourseMembership([course({ membershipRole: 'student' })])).toBe(false)
  })
})
