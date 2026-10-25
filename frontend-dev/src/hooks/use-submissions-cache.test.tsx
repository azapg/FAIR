import type { ReactNode } from 'react'
import { act, cleanup, renderHook, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider, useQuery } from '@tanstack/react-query'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

const { post, remove } = vi.hoisted(() => ({ post: vi.fn(), remove: vi.fn() }))
vi.mock('@/lib/api', () => ({ default: { post, delete: remove } }))
vi.mock('sonner', () => ({ toast: { success: vi.fn(), error: vi.fn() } }))

import {
  useCreateStudentSubmission,
  useDeleteSubmission,
  useReturnSubmission,
  useReturnSubmissions,
} from './use-submissions'

const gradeKeys = [
  ['lms', 'gradebook', 'course-1'],
  ['lms', 'student-grades', 'course-1'],
  ['lms', 'student-dashboard'],
]

afterEach(cleanup)
beforeEach(() => { post.mockReset(); remove.mockReset() })

describe('submission changes refresh current grades', () => {
  it.each(['create', 'return', 'bulk return', 'delete'] as const)(
    'refreshes active and cached LMS views after %s', async (operation) => {
      const client = new QueryClient({ defaultOptions: { queries: { retry: false, staleTime: Infinity } } })
      for (const key of gradeKeys) client.setQueryData(key, 80)
      client.setQueryData(['lms', 'student-grades', 'cached-course'], 80)
      let serverGrade: number | null = 80
      const succeed = async () => {
        serverGrade = operation === 'create' ? null : 95
        return { data: { id: 'attempt-2', assignmentId: 'assignment-1' } }
      }
      post.mockImplementation(succeed)
      remove.mockImplementation(succeed)
      const wrapper = ({ children }: { children: ReactNode }) => (
        <QueryClientProvider client={client}>{children}</QueryClientProvider>
      )
      const { result } = renderHook(() => ({
        book: useQuery({ queryKey: gradeKeys[0], queryFn: async () => serverGrade }),
        grades: useQuery({ queryKey: gradeKeys[1], queryFn: async () => serverGrade }),
        dashboard: useQuery({ queryKey: gradeKeys[2], queryFn: async () => serverGrade }),
        create: useCreateStudentSubmission(),
        release: useReturnSubmission(),
        bulkRelease: useReturnSubmissions(),
        remove: useDeleteSubmission(),
      }), { wrapper })

      await act(async () => {
        if (operation === 'create') await result.current.create.mutateAsync({ assignment_id: 'assignment-1' })
        if (operation === 'return') await result.current.release.mutateAsync('attempt-2')
        if (operation === 'bulk return') await result.current.bulkRelease.mutateAsync(['attempt-2'])
        if (operation === 'delete') await result.current.remove.mutateAsync('attempt-1')
      })
      await waitFor(() => {
        expect(result.current.book.data).toBe(serverGrade)
        expect(result.current.grades.data).toBe(serverGrade)
        expect(result.current.dashboard.data).toBe(serverGrade)
      })
      expect(client.getQueryState(['lms', 'student-grades', 'cached-course'])?.isInvalidated).toBe(true)
      client.clear()
    },
  )

  it('keeps the prior cached evidence when resubmission fails', async () => {
    const client = new QueryClient()
    for (const key of gradeKeys) client.setQueryData(key, 80)
    post.mockRejectedValue(new Error('Resubmissions prohibited'))
    const wrapper = ({ children }: { children: ReactNode }) => (
      <QueryClientProvider client={client}>{children}</QueryClientProvider>
    )
    const { result } = renderHook(() => useCreateStudentSubmission(), { wrapper })
    await act(async () => {
      await expect(result.current.mutateAsync({ assignment_id: 'assignment-1' })).rejects.toThrow('Resubmissions prohibited')
    })
    for (const key of gradeKeys) {
      expect(client.getQueryData(key)).toBe(80)
      expect(client.getQueryState(key)?.isInvalidated).toBe(false)
    }
    client.clear()
  })
})
