import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { StudentGradesTab } from './student-grades-tab'

const useStudentCourseGrades = vi.fn()

vi.mock('@/hooks/use-student-dashboard', () => ({
  useStudentCourseGrades: () => useStudentCourseGrades(),
}))

describe('StudentGradesTab', () => {
  beforeEach(() => {
    useStudentCourseGrades.mockReturnValue({
      isLoading: false,
      isError: false,
      data: {
        courseId: 'course-1',
        courseName: 'Biology',
        currentGradeLabel: 'Current grade',
        finalGradeAvailable: false,
        total: { pointsEarned: 18, pointsPossible: 20, percentage: 90, provisional: true, gradedItemCount: 1, excusedItemCount: 0, missingEntryCount: 2, reasons: ['2 relevant grade entries are not released'], calculation: 'points', configuredWeightTotal: null },
        categories: [{ id: 'category-1', name: 'Assignments', position: 0, aggregationStrategy: 'sum', isDefault: true }],
        categoryTotals: [{ categoryId: 'category-1', pointsEarned: 18, pointsPossible: 20, percentage: 90, provisional: true, gradedItemCount: 1, excusedItemCount: 0, missingEntryCount: 2, reasons: [], weight: null }],
        items: [
          { gradeItemId: 'item-1', categoryId: 'category-1', title: 'Lab notebook', maxPoints: 20, status: 'graded', pointsEarned: 18, note: 'Strong observations', assignmentId: 'assignment-1', contributionPercentagePoints: 90 },
          { gradeItemId: 'item-2', categoryId: 'category-1', title: 'Quiz', maxPoints: 10, status: 'missing', assignmentId: 'assignment-2' },
          { gradeItemId: 'item-3', categoryId: 'category-1', title: null, maxPoints: null, status: 'unreleased' },
        ],
      },
    })
  })

  it('explains the canonical current total and all learner-safe states', () => {
    render(<MemoryRouter><StudentGradesTab courseId="course-1" /></MemoryRouter>)

    expect(screen.getByRole('heading', { name: 'Grades' })).toBeInTheDocument()
    expect(screen.getByText('90%', { selector: '[data-slot="card-title"]' })).toBeInTheDocument()
    expect(screen.getByText('Not available yet')).toBeInTheDocument()
    expect(screen.getByText(/Missing and unreleased entries are not silently treated as zero/)).toBeInTheDocument()
    expect(screen.getByText('Strong observations')).toBeInTheDocument()
    expect(screen.getAllByText('Missing')).toHaveLength(2)
    expect(screen.getByText('Unreleased item')).toBeInTheDocument()
    expect(screen.getByText('90 percentage points')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /Lab notebook/ })).toHaveAttribute('href', '/courses/course-1/assignments/assignment-1')
  })
})
