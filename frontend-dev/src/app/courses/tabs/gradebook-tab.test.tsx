import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { GradebookTab } from './gradebook-tab'

const useCourseGradebook = vi.fn()
const useGradingQueue = vi.fn()

vi.mock('@/hooks/use-lms', async () => {
  const actual = await vi.importActual<typeof import('@/hooks/use-lms')>('@/hooks/use-lms')
  return {
    ...actual,
    useCourseGradebook: () => useCourseGradebook(),
    useGradingQueue: () => useGradingQueue(),
  }
})

function renderGradebook(isArchived = false) {
  return render(
    <QueryClientProvider client={new QueryClient()}>
      <MemoryRouter><GradebookTab courseId="course-1" isArchived={isArchived} /></MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('GradebookTab', () => {
  afterEach(cleanup)

  beforeEach(() => {
    useGradingQueue.mockReturnValue({ data: [] })
    useCourseGradebook.mockReturnValue({
      isLoading: false,
      data: {
        courseId: 'course-1',
        assignments: [{ id: 'assignment-1', title: 'Essay', maxGrade: { type: 'points', value: 100 } }],
        categories: [
          { id: 'category-1', name: 'Assignments', position: 0, aggregationStrategy: 'sum', isDefault: true },
          { id: 'category-2', name: 'Projects', position: 1, weight: 40, aggregationStrategy: 'sum', isDefault: false },
        ],
        items: [
          { id: 'item-1', categoryId: 'category-1', title: 'Essay', position: 0, maxPoints: 100, sourceType: 'assignment', sourceId: 'assignment-1', isManual: false },
          { id: 'item-2', categoryId: 'category-2', title: 'Presentation', position: 1, maxPoints: 20, isManual: true },
        ],
        rows: [{
          userId: 'student-1',
          name: 'Ada Student',
          email: 'ada@example.com',
          cells: [{ assignmentId: 'assignment-1', state: 'returned', score: 90, isLate: false, attemptCount: 1 }],
          itemCells: [
            { gradeItemId: 'item-1', status: 'graded', releaseState: 'released', pointsEarned: 90 },
            { gradeItemId: 'item-2', status: 'absent', releaseState: 'absent' },
          ],
          categoryTotals: [],
          courseTotal: {
            pointsEarned: 90,
            pointsPossible: 100,
            percentage: 90,
            provisional: true,
            gradedItemCount: 1,
            excusedItemCount: 0,
            missingEntryCount: 1,
            reasons: ['1 relevant grade entry is not released'],
            calculation: 'category_weighted',
            configuredWeightTotal: 40,
          },
        }],
      },
    })
  })

  it('shows additive category, manual-entry, total, and queue controls', () => {
    renderGradebook()
    expect(screen.getByRole('heading', { name: 'Gradebook' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Add category' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Edit Assignments' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Edit Projects' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Add manual item' })).toBeInTheDocument()
    expect(screen.getByText('Presentation')).toBeInTheDocument()
    expect(screen.getByText('90 / 100 · 90%')).toBeInTheDocument()
    expect(screen.getByText('Totals are provisional')).toBeInTheDocument()
    expect(screen.getByText('Nothing needs grading.')).toBeInTheDocument()
    expect(screen.getByText('1 attempt · released')).toBeInTheDocument()
  })

  it('preserves submitted, attempt-count, and late legacy state before release', () => {
    useCourseGradebook.mockReturnValueOnce({
      isLoading: false,
      data: {
        courseId: 'course-1',
        assignments: [{ id: 'assignment-1', title: 'Essay', maxGrade: { type: 'points', value: 100 } }],
        categories: [{ id: 'category-1', name: 'Assignments', position: 0, aggregationStrategy: 'sum', isDefault: true }],
        items: [{ id: 'item-1', categoryId: 'category-1', title: 'Essay', position: 0, maxPoints: 100, sourceType: 'assignment', sourceId: 'assignment-1', isManual: false }],
        rows: [{
          userId: 'student-1',
          name: 'Ada Student',
          email: 'ada@example.com',
          cells: [{ assignmentId: 'assignment-1', state: 'submitted', isLate: true, attemptCount: 2 }],
          itemCells: [{ gradeItemId: 'item-1', status: 'absent', releaseState: 'absent' }],
          categoryTotals: [],
          courseTotal: null,
        }],
      },
    })
    renderGradebook()
    expect(screen.getByText('submitted')).toBeInTheDocument()
    expect(screen.getByText('2 attempts · late')).toBeInTheDocument()
  })

  it('hides mutation controls for archived courses', () => {
    renderGradebook(true)
    expect(screen.getByText('Archived · read-only')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Add category' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Add manual item' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Edit Assignments' })).not.toBeInTheDocument()
    expect(screen.queryByText('Add points')).not.toBeInTheDocument()
  })
})
