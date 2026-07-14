import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const { useStudentTodo } = vi.hoisted(() => ({ useStudentTodo: vi.fn() }))

vi.mock('@/hooks/use-lms', () => ({ useStudentTodo }))
vi.mock('@/components/breadcrumb-nav', () => ({ BreadcrumbNav: () => null }))

import TodoPage from './page'

describe('TodoPage', () => {
  beforeEach(() => useStudentTodo.mockReset())

  it('links missing and submitted work to the assignment', () => {
    useStudentTodo.mockReturnValue({
      isLoading: false,
      data: [{
        assignmentId: 'assignment-1',
        assignmentTitle: 'Cell diagram',
        courseId: 'course-1',
        courseName: 'Biology',
        deadline: '2026-07-15T12:00:00Z',
        state: 'missing',
        attemptCount: 0,
        isLate: false,
      }],
    })

    render(<MemoryRouter><TodoPage /></MemoryRouter>)

    expect(screen.getByRole('heading', { name: 'To-do' })).toBeInTheDocument()
    expect(screen.getByText('Cell diagram')).toBeInTheDocument()
    expect(screen.getByText('missing')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /Cell diagram/ })).toHaveAttribute(
      'href',
      '/courses/course-1/assignments/assignment-1',
    )
  })

  it('shows an all caught up state', () => {
    useStudentTodo.mockReturnValue({ isLoading: false, data: [] })
    render(<MemoryRouter><TodoPage /></MemoryRouter>)
    expect(screen.getByText('You are all caught up.')).toBeInTheDocument()
  })
})
