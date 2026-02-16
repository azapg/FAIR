import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import api from '@/lib/api'
import { Assignment } from "@/hooks/use-assignments";
import { toast } from 'sonner';

export type Course = {
  id: string
  name: string
  description?: string | null
  instructorId: string
  instructorName?: string
  assignmentsCount: number
  enrollmentCode?: string | null
  isEnrollmentEnabled: boolean | null
}

export type CourseDetail = {
  id: string,
  name: string,
  description?: string | null,
  instructor: {
    id: string,
    name: string,
    email: string,
    role: 'professor' | 'admin' | 'student',
  },
  assignments: Assignment[],
  workflows: {
    id: string,
    name: string,
    description?: string | null,
    createdAt: string,
    updatedAt: string,
  }
  enrollmentCode?: string | null
  isEnrollmentEnabled: boolean | null
}

export type CreateCourseInput = {
  name: string
  description?: string | null
  instructorId: string
}

export type UpdateCourseInput = Partial<Pick<Course, 'name' | 'description'>>

export type CourseSettingsInput = Partial<Pick<Course, 'isEnrollmentEnabled'>>

export type EnrollmentSummary = {
  id: string
  userId: string
  courseId: string
  enrolledAt: string
  userName?: string
  courseName?: string
}

export type ListParams = Record<string, string | number | boolean | null | undefined>

export const coursesKeys = {
  all: ['courses'] as const,
  lists: () => [...coursesKeys.all, 'list'] as const,
  list: (params?: ListParams) => [...coursesKeys.lists(), { params }] as const,
  details: () => [...coursesKeys.all, 'detail'] as const,
  detail: (id: string) => [...coursesKeys.details(), id] as const,
}

const fetchCourses = async (params?: ListParams): Promise<Course[]> => {
  const res = await api.get('/courses', { params })
  return res.data
}

const fetchCourse = async (id: string, detailed: boolean = false): Promise<Course | CourseDetail> => {
  const res = await api.get(`/courses/${id}?detailed=${detailed}`)
  return res.data
}

const createCourse = async (data: CreateCourseInput): Promise<Course> => {
  const res = await api.post('/courses', data)
  return res.data
}

const updateCourse = async (id: string, data: UpdateCourseInput): Promise<Course> => {
  const res = await api.put(`/courses/${id}`, data)
  return res.data
}

const deleteCourse = async (id: string): Promise<void> => {
  await api.delete(`/courses/${id}`)
}

const resetEnrollmentCode = async (id: string): Promise<Course> => {
  const res = await api.post(`/courses/${id}/reset-code`)
  return res.data
}

const updateCourseSettingsApi = async (id: string, data: CourseSettingsInput): Promise<Course> => {
  const res = await api.patch(`/courses/${id}/settings`, data)
  return res.data
}

const joinCourseByCode = async (code: string): Promise<EnrollmentSummary> => {
  const res = await api.post('/enrollments/join', { code })
  return res.data
}

export function useCourses(params?: ListParams, enabled = true) {
  return useQuery({
    queryKey: coursesKeys.list(params),
    queryFn: () => fetchCourses(params),
    enabled,
  })
}

export function useCourse(id?: string, enabled = true, detailed = false) {
  return useQuery({
    queryKey: id != null
      ? [...coursesKeys.detail(id), { detailed }]
      : [...coursesKeys.detail('unknown'), { detailed }],
    queryFn: () => fetchCourse(id as string, detailed),
    enabled: enabled && id != null,
  })
}

export function useCreateCourse() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: CreateCourseInput) => createCourse(data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: coursesKeys.lists() })
      toast.success('Course created successfully');
    },
    onError: (error: Error) => {
      toast.error('Failed to create Course', {
        description: error.message || 'Something went wrong'
      });
    }
  })
}

export function useUpdateCourse() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: UpdateCourseInput }) => updateCourse(id, data),
    onSuccess: (_course, vars) => {
      qc.invalidateQueries({ queryKey: coursesKeys.detail(vars.id) })
      qc.invalidateQueries({ queryKey: coursesKeys.lists() })
      toast.success('Course updated successfully');
    },
    onError: (error: Error) => {
      toast.error('Failed to update Course', {
        description: error.message || 'Something went wrong'
      });
    }
  })
}

export function useDeleteCourse() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => deleteCourse(id),
    onSuccess: (_void, id) => {
      qc.invalidateQueries({ queryKey: coursesKeys.detail(id) })
      qc.invalidateQueries({ queryKey: coursesKeys.lists() })
      toast.success('Course deleted successfully');
    },
    onError: (error: Error) => {
      toast.error('Failed to delete Course', {
        description: error.message || 'Something went wrong'
      });
    }
  })
}

export function useResetEnrollmentCode() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => resetEnrollmentCode(id),
    onSuccess: (_course, id) => {
      qc.invalidateQueries({ queryKey: coursesKeys.detail(id) })
      qc.invalidateQueries({ queryKey: coursesKeys.lists() })
      toast.success('Enrollment code reset');
    },
    onError: (error: Error) => {
      toast.error('Failed to reset enrollment code', {
        description: error.message || 'Something went wrong'
      });
    }
  })
}

export function useUpdateCourseSettings() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: CourseSettingsInput }) => updateCourseSettingsApi(id, data),
    onSuccess: (_course, vars) => {
      qc.invalidateQueries({ queryKey: coursesKeys.detail(vars.id) })
      qc.invalidateQueries({ queryKey: coursesKeys.lists() })
      toast.success('Course settings updated');
    },
    onError: (error: Error) => {
      toast.error('Failed to update course settings', {
        description: error.message || 'Something went wrong'
      });
    }
  })
}

export function useJoinCourseByCode() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (code: string) => joinCourseByCode(code),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: coursesKeys.lists() })
      toast.success('Joined course successfully');
    },
    onError: (error: Error) => {
      toast.error('Failed to join course', {
        description: error.message || 'Please verify the class code and try again'
      });
    }
  })
}
