import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import api from '@/lib/api'
import { LmsArtifact } from '@/hooks/use-artifacts'
import { toast } from 'sonner'

export type CoursePost = {
  id: string
  courseId: string
  authorId: string
  authorName: string
  kind: 'announcement' | 'material'
  title: string
  body?: string | null
  artifacts: LmsArtifact[]
  commentsCount: number
  createdAt: string
  updatedAt: string
}

export type CourseComment = {
  id: string
  postId: string
  authorId: string
  authorName: string
  body: string
  createdAt: string
  updatedAt: string
}

export type Notification = {
  id: string
  kind: string
  title: string
  body?: string | null
  link?: string | null
  createdAt: string
  readAt?: string | null
}

export type SubmissionComment = {
  id: string
  submissionId: string
  authorId: string
  authorName: string
  body: string
  createdAt: string
  updatedAt: string
}

export function useCoursePosts(courseId?: string) {
  return useQuery({
    queryKey: ['lms', 'posts', courseId],
    queryFn: async (): Promise<CoursePost[]> =>
      (await api.get(`/lms/courses/${courseId}/posts`)).data,
    enabled: Boolean(courseId),
  })
}

export function useCreateCoursePost(courseId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async (data: { title: string; body?: string; kind?: CoursePost['kind'] }) =>
      (await api.post(`/lms/courses/${courseId}/posts`, data)).data as CoursePost,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['lms', 'posts', courseId] })
      toast.success('Posted to class')
    },
  })
}

export function usePostComments(postId: string) {
  return useQuery({
    queryKey: ['lms', 'comments', postId],
    queryFn: async (): Promise<CourseComment[]> =>
      (await api.get(`/lms/posts/${postId}/comments`)).data,
  })
}

export function useCreatePostComment(postId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async (body: string) =>
      (await api.post(`/lms/posts/${postId}/comments`, { body })).data as CourseComment,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['lms', 'comments', postId] })
      qc.invalidateQueries({ queryKey: ['lms', 'posts'] })
    },
  })
}

export function useNotifications(enabled = true) {
  return useQuery({
    queryKey: ['lms', 'notifications'],
    queryFn: async (): Promise<Notification[]> =>
      (await api.get('/lms/notifications')).data,
    enabled,
    refetchInterval: 60_000,
  })
}

export function useReadNotification() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async (id: string) =>
      (await api.post(`/lms/notifications/${id}/read`)).data as Notification,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['lms', 'notifications'] }),
  })
}

export function useReadAllNotifications() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async () => api.post('/lms/notifications/read-all'),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['lms', 'notifications'] }),
  })
}

export function useSubmissionComments(submissionId: string) {
  return useQuery({
    queryKey: ['lms', 'submission-comments', submissionId],
    queryFn: async (): Promise<SubmissionComment[]> =>
      (await api.get(`/lms/submissions/${submissionId}/comments`)).data,
    enabled: Boolean(submissionId),
  })
}

export function useCreateSubmissionComment(submissionId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async (body: string) =>
      (await api.post(`/lms/submissions/${submissionId}/comments`, { body })).data as SubmissionComment,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['lms', 'submission-comments', submissionId] })
      toast.success('Private comment sent')
    },
  })
}
