import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { CourseCopyDialog } from './course-copy-dialog'

const mocks = vi.hoisted(() => ({
  previewCourseCopy: vi.fn(),
  copyCourse: vi.fn(),
  saveCourseTemplate: vi.fn(),
}))

vi.mock('@/hooks/use-courses', () => mocks)

describe('CourseCopyDialog', () => {
  afterEach(cleanup)

  beforeEach(() => {
    mocks.previewCourseCopy.mockReset().mockResolvedValue({
      copied: { assignments: 2, sections: 1 },
      transformed: { dates_cleared: 2 },
      skipped: { submissions: 4, grade_entries: 2 },
      unsupported: { file_items: 1 },
      datePolicy: 'clear',
      dateShiftDays: 0,
      warnings: ['One protected file item cannot be copied.'],
    })
    mocks.copyCourse.mockReset()
    mocks.saveCourseTemplate.mockReset().mockResolvedValue(undefined)
  })

  it('requires a fresh preview before creating a draft copy', async () => {
    render(<CourseCopyDialog courseId="course-1" name="Source" />)

    fireEvent.click(screen.getByRole('button', { name: 'Copy course' }))

    expect(screen.getByRole('button', { name: 'Preview copy' })).toBeTruthy()
    expect(screen.queryByRole('button', { name: 'Create draft copy' })).toBeNull()

    fireEvent.click(screen.getByRole('button', { name: 'Preview copy' }))

    expect(await screen.findByLabelText('Course copy preview')).toHaveTextContent(
      '2 assignments',
    )
    expect(screen.getByLabelText('Course copy preview')).toHaveTextContent(
      'One protected file item cannot be copied.',
    )
    expect(screen.getByRole('button', { name: 'Create draft copy' })).toBeTruthy()

    expect(mocks.previewCourseCopy).toHaveBeenCalledWith(
      'course-1',
      expect.objectContaining({
        name: 'Source copy',
        datePolicy: 'clear',
        dateShiftDays: 0,
        selection: expect.objectContaining({ flows: true, quizzes: true }),
        idempotencyKey: expect.any(String),
      }),
    )
  })

  it('invalidates the preview when the selection changes', async () => {
    render(<CourseCopyDialog courseId="course-1" name="Source" />)
    fireEvent.click(screen.getByRole('button', { name: 'Copy course' }))
    fireEvent.click(screen.getByRole('button', { name: 'Preview copy' }))
    await waitFor(() =>
      expect(screen.getByRole('button', { name: 'Create draft copy' })).not.toBeDisabled(),
    )

    fireEvent.click(screen.getByRole('checkbox', { name: 'Flow definitions' }))

    await waitFor(() =>
      expect(screen.queryByLabelText('Course copy preview')).toBeNull(),
    )
    expect(screen.getByRole('button', { name: 'Preview copy' })).toBeTruthy()
  })

  it('saves private templates with the selected copy defaults', async () => {
    render(<CourseCopyDialog courseId="course-1" name="Source" />)
    fireEvent.click(screen.getByRole('button', { name: 'Copy course' }))
    fireEvent.click(screen.getByRole('checkbox', { name: 'Flow definitions' }))
    fireEvent.click(screen.getByRole('button', { name: 'Save private template' }))

    await waitFor(() =>
      expect(mocks.saveCourseTemplate).toHaveBeenCalledWith('course-1', {
        name: 'Source copy',
        datePolicy: 'clear',
        dateShiftDays: 0,
        selection: expect.objectContaining({ flows: false, assignments: true }),
      }),
    )
  })

  it('keeps a failed durable job available for a safe retry', async () => {
    mocks.copyCourse.mockResolvedValue({
      jobId: 'job-1',
      status: 'failed',
      destinationCourseId: null,
      mapping: {},
      errorMessage: 'A source item changed during copy.',
      completedAt: null,
    })
    render(<CourseCopyDialog courseId="course-1" name="Source" />)
    fireEvent.click(screen.getByRole('button', { name: 'Copy course' }))
    fireEvent.click(screen.getByRole('button', { name: 'Preview copy' }))
    fireEvent.click(await screen.findByRole('button', { name: 'Create draft copy' }))

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'A source item changed during copy.',
    )
    expect(screen.getByRole('button', { name: 'Retry safe copy' })).toBeTruthy()
  })
})
