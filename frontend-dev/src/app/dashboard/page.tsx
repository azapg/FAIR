import { AlertCircle, BookOpenCheck, CalendarClock, MessageSquareText } from 'lucide-react'
import { Link } from 'react-router-dom'

import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import {
  StudentDashboardWorkItem,
  useStudentDashboard,
} from '@/hooks/use-student-dashboard'

const number = new Intl.NumberFormat(undefined, { maximumFractionDigits: 1 })

function formatDate(value?: string | null, timezoneName = 'UTC') {
  if (!value) return 'No due date'
  try {
    return new Intl.DateTimeFormat(undefined, {
      dateStyle: 'medium',
      timeStyle: 'short',
      timeZone: timezoneName,
      timeZoneName: 'short',
    }).format(new Date(value))
  } catch {
    return new Date(value).toLocaleString()
  }
}

function DashboardLoading() {
  return (
    <div role="status" aria-live="polite" className="space-y-5 px-4 py-6 sm:px-6">
      <span className="sr-only">Loading student dashboard</span>
      <Skeleton className="h-9 w-48" />
      <div className="grid gap-4 lg:grid-cols-2">
        <Skeleton className="h-56 w-full" />
        <Skeleton className="h-56 w-full" />
      </div>
    </div>
  )
}

function WorkList({ items, empty }: { items: StudentDashboardWorkItem[]; empty: string }) {
  if (items.length === 0) return <p className="text-sm text-muted-foreground">{empty}</p>
  return (
    <ul className="space-y-2">
      {items.map((item) => (
        <li key={item.assignmentId}>
          <Link
            to={`/courses/${item.courseId}/assignments/${item.assignmentId}`}
            className="block min-w-0 rounded-lg border p-3 transition-colors hover:bg-muted/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          >
            <div className="break-words font-medium">{item.title}</div>
            <div className="mt-1 break-words text-sm text-muted-foreground">{item.courseName}</div>
            <div className="mt-2 text-xs text-muted-foreground">
              {formatDate(item.deadline, item.timezoneName)}
              {item.state === 'submitted' ? ' · Submitted' : ''}
            </div>
          </Link>
        </li>
      ))}
    </ul>
  )
}

export default function StudentDashboardPage() {
  const { data, isLoading, isError, refetch } = useStudentDashboard()

  if (isLoading) return <DashboardLoading />
  if (isError || !data) {
    return (
      <main className="px-4 py-6 sm:px-6">
        <Alert variant="destructive">
          <AlertCircle />
          <AlertTitle>Student dashboard unavailable</AlertTitle>
          <AlertDescription>
            <p>We could not load your learner view. This page is only available to learner-only accounts.</p>
            <button type="button" className="font-medium underline" onClick={() => refetch()}>Try again</button>
          </AlertDescription>
        </Alert>
      </main>
    )
  }

  const unavailable = data.sources.filter((source) => !source.available)

  return (
    <main className="min-w-0 space-y-6 px-4 py-6 sm:px-6">
      <header>
        <h1 className="text-base leading-5 font-medium">Dashboard</h1>
        <p className="mt-1 text-sm text-muted-foreground">Your released grades, course progress, and work across active courses.</p>
      </header>

      {unavailable.length > 0 && (
        <Alert>
          <AlertCircle />
          <AlertTitle>Some information is temporarily unavailable</AlertTitle>
          <AlertDescription>{unavailable.map((source) => source.message).filter(Boolean).join(' · ')}</AlertDescription>
        </Alert>
      )}

      <section aria-labelledby="course-progress-heading">
        <div className="mb-3 flex items-center gap-2">
          <BookOpenCheck className="size-5" aria-hidden="true" />
          <h2 id="course-progress-heading" className="text-base leading-5 font-medium">Course progress</h2>
        </div>
        {data.courseProgress.length === 0 ? (
          <Card><CardContent className="text-sm text-muted-foreground">No active course progress yet.</CardContent></Card>
        ) : (
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
            {data.courseProgress.map((course) => (
              <Card key={course.courseId} className="min-w-0 gap-4">
                <CardHeader>
                  <CardTitle className="break-words text-base">
                    <Link className="hover:underline" to={`/courses/${course.courseId}/grades`}>{course.courseName}</Link>
                  </CardTitle>
                  <CardDescription>{course.term || 'Active course'}</CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div>
                    <div className="flex justify-between gap-3 text-sm"><span>Content complete</span><span>{course.completedItems}/{course.trackedItems}</span></div>
                    <div
                      role="progressbar"
                      aria-label={`${course.courseName} content completion`}
                      aria-valuemin={0}
                      aria-valuemax={100}
                      aria-valuenow={course.completionPercentage ?? 0}
                      className="mt-2 h-2 overflow-hidden rounded-full bg-muted"
                    >
                      <div className="h-full bg-primary" style={{ width: `${Math.min(100, course.completionPercentage ?? 0)}%` }} />
                    </div>
                  </div>
                  <div className="flex flex-wrap items-end justify-between gap-2">
                    <div><div className="text-xs text-muted-foreground">Current grade</div><div className="text-xl leading-6 font-medium">{course.currentGrade == null ? '—' : `${number.format(course.currentGrade)}%`}</div></div>
                    {course.gradeIsProvisional && <Badge variant="outline">Provisional</Badge>}
                  </div>
                  <div className="text-xs text-muted-foreground">{number.format(course.pointsEarned)} / {number.format(course.pointsPossible)} released points</div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </section>

      <div className="grid min-w-0 gap-4 lg:grid-cols-2">
        <Card className="min-w-0">
          <CardHeader><CardTitle className="flex items-center gap-2"><CalendarClock className="size-5" aria-hidden="true" />Overdue</CardTitle></CardHeader>
          <CardContent><WorkList items={data.overdueWork} empty="Nothing overdue." /></CardContent>
        </Card>
        <Card className="min-w-0">
          <CardHeader><CardTitle className="flex items-center gap-2"><CalendarClock className="size-5" aria-hidden="true" />Upcoming</CardTitle></CardHeader>
          <CardContent><WorkList items={data.upcomingWork} empty="No upcoming work." /></CardContent>
        </Card>
      </div>

      <div className="grid min-w-0 gap-4 lg:grid-cols-2">
        <Card className="min-w-0">
          <CardHeader><CardTitle className="flex items-center gap-2"><MessageSquareText className="size-5" aria-hidden="true" />Returned feedback</CardTitle></CardHeader>
          <CardContent>
            {data.returnedFeedback.length === 0 ? <p className="text-sm text-muted-foreground">No recently returned feedback.</p> : (
              <ul className="space-y-2">
                {data.returnedFeedback.map((item) => (
                  <li key={item.submissionId}>
                    <Link to={item.link} className="block min-w-0 rounded-lg border p-3 hover:bg-muted/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring">
                      <div className="break-words font-medium">{item.assignmentTitle}</div>
                      <div className="mt-1 break-words text-sm text-muted-foreground">{item.courseName}</div>
                      <div className="mt-2 flex flex-wrap gap-2 text-xs text-muted-foreground">
                        {item.pointsEarned != null && item.maxPoints != null && <span>{number.format(item.pointsEarned)} / {number.format(item.maxPoints)} points</span>}
                        {item.feedbackAvailable && <Badge variant="secondary">Feedback available</Badge>}
                      </div>
                    </Link>
                  </li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>

        <Card className="min-w-0">
          <CardHeader><CardTitle>Recent course activity</CardTitle></CardHeader>
          <CardContent>
            {data.recentActivity.length === 0 ? <p className="text-sm text-muted-foreground">No recent activity.</p> : (
              <ul className="space-y-2">
                {data.recentActivity.map((item) => (
                  <li key={`${item.kind}-${item.id}`}>
                    <Link to={item.link} className="block min-w-0 rounded-lg border p-3 hover:bg-muted/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring">
                      <div className="flex min-w-0 flex-wrap items-center gap-2"><Badge variant="outline" className="capitalize">{item.kind}</Badge><span className="min-w-0 break-words font-medium">{item.title}</span></div>
                      <div className="mt-1 break-words text-sm text-muted-foreground">{item.courseName}</div>
                    </Link>
                  </li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>
      </div>
    </main>
  )
}
