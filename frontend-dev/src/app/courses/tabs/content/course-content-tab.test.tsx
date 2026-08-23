import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'


const mocks = vi.hoisted(() => ({
  apiGet: vi.fn(),
  content: vi.fn(),
  reorderSections: vi.fn(),
  reorderItems: vi.fn(),
}))

function mutation(mutate = vi.fn()) {
  return { mutate, mutateAsync: vi.fn(), isPending: false }
}

vi.mock('@/lib/api', () => ({
  default: { get: mocks.apiGet },
  getApiBaseUrl: () => 'http://localhost:8000/api',
}))

vi.mock('@/hooks/use-artifacts', () => ({
  useArtifacts: () => ({
    data: [{
      id: 'file-1',
      title: 'Syllabus',
      artifactType: 'file',
      mime: 'text/plain',
      creatorId: 'owner-1',
      createdAt: '2026-08-12T00:00:00Z',
      updatedAt: '2026-08-12T00:00:00Z',
      status: 'attached',
      courseId: 'course-1',
      accessLevel: 'course',
    }],
  }),
}))

vi.mock('@/hooks/use-course-content', () => ({
  useCourseContent: (...args: unknown[]) => mocks.content(...args),
  useCreateCourseSection: () => mutation(),
  useUpdateCourseSection: () => mutation(),
  useDeleteCourseSection: () => mutation(),
  useReorderCourseSections: () => mutation(mocks.reorderSections),
  useCreateCourseItem: () => mutation(),
  useUpdateCourseItem: () => mutation(),
  useDeleteCourseItem: () => mutation(),
  useReorderCourseItems: () => mutation(mocks.reorderItems),
}))

import { CourseContentTab } from './course-content-tab'


const content = {
  courseId: 'course-1',
  canManage: true,
  sections: [
    {
      id: 'section-1',
      courseId: 'course-1',
      title: 'Overview',
      summary: 'Start here',
      position: 0,
      visibility: 'published',
      createdAt: '2026-08-12T00:00:00Z',
      updatedAt: '2026-08-12T00:00:00Z',
      items: [
        {
          id: 'page-1',
          courseId: 'course-1',
          sectionId: 'section-1',
          title: 'Welcome',
          position: 0,
          kind: 'page',
          visibility: 'published',
          payload: { body: 'Welcome to **FAIR**.' },
          createdAt: '2026-08-12T00:00:00Z',
          updatedAt: '2026-08-12T00:00:00Z',
        },
        {
          id: 'file-item-1',
          courseId: 'course-1',
          sectionId: 'section-1',
          title: 'Syllabus',
          position: 1,
          kind: 'file',
          visibility: 'published',
          resourceId: 'file-1',
          payload: {},
          createdAt: '2026-08-12T00:00:00Z',
          updatedAt: '2026-08-12T00:00:00Z',
        },
      ],
    },
    {
      id: 'section-2',
      courseId: 'course-1',
      title: 'Week one',
      position: 1,
      visibility: 'draft',
      createdAt: '2026-08-12T00:00:00Z',
      updatedAt: '2026-08-12T00:00:00Z',
      items: [],
    },
  ],
}


describe('CourseContentTab', () => {
  afterEach(cleanup)

  beforeEach(() => {
    vi.clearAllMocks()
    mocks.content.mockReturnValue({ data: content, isLoading: false, isError: false })
    mocks.apiGet.mockImplementation(async (url: string) => {
      if (url === '/v1/artifacts/file-1/download') {
        return { data: { url: '/api/v1/artifact-storage/local/syllabus.txt' } }
      }
      return { data: 'Authenticated syllabus text' }
    })
  })

  it('offers keyboard-accessible move controls with exact reordered membership', () => {
    render(
      <MemoryRouter>
        <CourseContentTab courseId="course-1" canManage isArchived={false} assignments={[]} />
      </MemoryRouter>,
    )

    fireEvent.click(screen.getByRole('button', { name: 'Move Overview section down' }))
    expect(mocks.reorderSections).toHaveBeenCalledWith(['section-2', 'section-1'])

    fireEvent.click(screen.getByRole('button', { name: 'Move Welcome down' }))
    expect(mocks.reorderItems).toHaveBeenCalledWith({
      sectionId: 'section-1',
      orderedIds: ['file-item-1', 'page-1'],
    })
  })

  it('opens protected files through the authenticated artifact action', async () => {
    render(
      <MemoryRouter>
        <CourseContentTab courseId="course-1" canManage isArchived={false} assignments={[]} />
      </MemoryRouter>,
    )

    const fileAction = screen.getByRole('button', { name: 'Syllabus' })
    expect(fileAction.closest('a')).toBeNull()
    fireEvent.click(fileAction)

    await waitFor(() => expect(mocks.apiGet).toHaveBeenCalledWith(
      '/v1/artifacts/file-1/download',
      expect.objectContaining({ responseType: 'json' }),
    ))
    expect(await screen.findByText('Authenticated syllabus text')).toBeInTheDocument()
  })

  it('renders the published learner outline without staff controls', () => {
    mocks.content.mockReturnValue({
      data: { ...content, canManage: false, sections: [content.sections[0]] },
      isLoading: false,
      isError: false,
    })
    render(
      <MemoryRouter>
        <CourseContentTab courseId="course-1" canManage={false} isArchived={false} assignments={[]} />
      </MemoryRouter>,
    )

    expect(screen.getByRole('heading', { name: 'Welcome' })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Add section' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /Move Overview/ })).not.toBeInTheDocument()
  })
})
