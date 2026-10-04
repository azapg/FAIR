import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import StudentDashboardPage from './page'

const useStudentDashboard = vi.fn()

vi.mock('@/hooks/use-student-dashboard', () => ({
  useStudentDashboard: () => useStudentDashboard(),
}))

describe('StudentDashboardPage', () => {
  beforeEach(() => {
    useStudentDashboard.mockReturnValue({
      isLoading: false,
      isError: false,
      data: {
        generatedAt: '2026-08-12T20:00:00Z',
        upcomingWork: [{ assignmentId: 'assignment-1', courseId: 'course-1', courseName: 'Biology', title: 'Cell diagram', deadline: '2026-08-14T17:00:00Z', timezoneName: 'America/Panama', state: 'upcoming' }],
        overdueWork: [],
        returnedFeedback: [{ assignmentId: 'assignment-2', submissionId: 'submission-1', courseId: 'course-1', courseName: 'Biology', assignmentTitle: 'Field notes', pointsEarned: 18, maxPoints: 20, feedbackAvailable: true, returnedAt: '2026-08-12T17:00:00Z', link: '/courses/course-1/grades' }],
        recentActivity: [{ id: 'post-1', courseId: 'course-1', courseName: 'Biology', kind: 'announcement', title: 'Lab update', occurredAt: '2026-08-12T18:00:00Z', link: '/courses/course-1/stream' }],
        courseProgress: [{ courseId: 'course-1', courseName: 'Biology', term: 'Fall 2026', completedItems: 2, trackedItems: 4, completionPercentage: 50, currentGrade: 90, pointsEarned: 18, pointsPossible: 20, gradeIsProvisional: true }],
        sources: [
          { source: 'work', available: true },
          { source: 'feedback', available: true },
          { source: 'activity', available: false, message: 'Activity data is temporarily unavailable' },
          { source: 'progress', available: true },
        ],
      },
    })
  })

  it('keeps useful learner sections visible when one source is partial', () => {
    render(<MemoryRouter><StudentDashboardPage /></MemoryRouter>)

    expect(screen.getByRole('heading', { name: 'Dashboard' })).toBeInTheDocument()
    expect(screen.getByText('Some information is temporarily unavailable')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /Cell diagram/ })).toHaveAttribute('href', '/courses/course-1/assignments/assignment-1')
    expect(screen.getByRole('link', { name: /Field notes/ })).toHaveAttribute('href', '/courses/course-1/grades')
    expect(screen.getByRole('progressbar', { name: 'Biology content completion' })).toHaveAttribute('aria-valuenow', '50')
    expect(screen.getByText('90%')).toBeInTheDocument()
  })

  it('announces its loading state', () => {
    useStudentDashboard.mockReturnValue({ isLoading: true })
    render(<MemoryRouter><StudentDashboardPage /></MemoryRouter>)
    expect(screen.getByRole('status')).toHaveTextContent('Loading student dashboard')
  })
})
