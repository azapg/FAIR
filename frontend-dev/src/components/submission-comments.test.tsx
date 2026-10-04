import { fireEvent, render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const { useSubmissionComments, mutate, useCreateSubmissionComment } = vi.hoisted(() => ({
  useSubmissionComments: vi.fn(),
  mutate: vi.fn(),
  useCreateSubmissionComment: vi.fn(),
}))

vi.mock('@/hooks/use-communication', () => ({
  useSubmissionComments,
  useCreateSubmissionComment,
}))

import { SubmissionComments } from './submission-comments'

describe('SubmissionComments', () => {
  beforeEach(() => {
    mutate.mockReset()
    useSubmissionComments.mockReturnValue({
      isLoading: false,
      data: [{ id: 'comment-1', authorName: 'Student', body: 'Please check this.' }],
    })
    useCreateSubmissionComment.mockReturnValue({ isPending: false, mutate })
  })

  it('renders the private thread and sends a comment', () => {
    render(<SubmissionComments submissionId="submission-1" />)
    expect(screen.getByText(/Visible only to this student and course staff/)).toBeInTheDocument()
    expect(screen.getByText('Please check this.')).toBeInTheDocument()

    fireEvent.change(screen.getByPlaceholderText('Write a private comment…'), {
      target: { value: 'Private reply' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Send' }))

    expect(mutate).toHaveBeenCalledWith('Private reply', expect.objectContaining({ onSuccess: expect.any(Function) }))
  })
})
