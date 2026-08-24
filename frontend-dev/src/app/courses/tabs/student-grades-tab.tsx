import { AlertCircle, Calculator } from 'lucide-react'
import { Link } from 'react-router-dom'

import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { StudentGradeItem, useStudentCourseGrades } from '@/hooks/use-student-dashboard'

const number = new Intl.NumberFormat(undefined, { maximumFractionDigits: 2 })

function format(value?: number | null) {
  return value == null ? '—' : number.format(value)
}

function statusLabel(item: StudentGradeItem) {
  if (item.status === 'graded') return 'Graded'
  if (item.status === 'excused') return 'Excused'
  if (item.status === 'missing') return 'Missing'
  return 'Unreleased'
}

export function StudentGradesTab({ courseId, enabled = true }: { courseId: string; enabled?: boolean }) {
  const { data, isLoading, isError, refetch } = useStudentCourseGrades(courseId, enabled)

  if (isLoading) {
    return <div role="status" aria-live="polite" className="space-y-3 py-5"><span className="sr-only">Loading grades</span><Skeleton className="h-32 w-full" /><Skeleton className="h-48 w-full" /></div>
  }
  if (isError || !data) {
    return (
      <Alert variant="destructive" className="my-4">
        <AlertCircle />
        <AlertTitle>Grades unavailable</AlertTitle>
        <AlertDescription><p>We could not load your released grades.</p><button type="button" className="font-medium underline" onClick={() => refetch()}>Try again</button></AlertDescription>
      </Alert>
    )
  }

  const explanation = data.total.calculation === 'category_weighted'
    ? 'The server combines released category percentages using their configured weights, normalized across categories that currently have released points.'
    : 'The server divides released points earned by released points possible. Missing and unreleased entries are not silently treated as zero.'

  return (
    <div className="min-w-0 space-y-5 py-4">
      <header>
        <h2 className="text-2xl font-semibold">Grades</h2>
        <p className="mt-1 text-sm text-muted-foreground">Only grades and feedback released to you appear here.</p>
      </header>

      <div className="grid gap-3 sm:grid-cols-3">
        <Card className="gap-3"><CardHeader><CardDescription>{data.currentGradeLabel}</CardDescription><CardTitle className="text-3xl">{data.total.percentage == null ? '—' : `${format(data.total.percentage)}%`}</CardTitle></CardHeader></Card>
        <Card className="gap-3"><CardHeader><CardDescription>Released points</CardDescription><CardTitle className="text-3xl">{format(data.total.pointsEarned)}</CardTitle></CardHeader><CardContent className="text-sm text-muted-foreground">out of {format(data.total.pointsPossible)} possible now</CardContent></Card>
        <Card className="gap-3"><CardHeader><CardDescription>Final grade</CardDescription><CardTitle className="text-lg">{data.finalGradeAvailable ? 'Available' : 'Not available yet'}</CardTitle></CardHeader><CardContent className="text-sm text-muted-foreground">{data.total.provisional ? `${data.total.missingEntryCount} item${data.total.missingEntryCount === 1 ? '' : 's'} missing or unreleased` : 'No unreleased items in this calculation'}</CardContent></Card>
      </div>

      {data.total.provisional && (
        <Alert>
          <AlertCircle />
          <AlertTitle>This is a current, provisional grade</AlertTitle>
          <AlertDescription>{data.total.reasons.join(' · ') || 'Some relevant grade information has not been released.'}</AlertDescription>
        </Alert>
      )}

      <Alert>
        <Calculator />
        <AlertTitle>How this total is calculated</AlertTitle>
        <AlertDescription>{explanation}</AlertDescription>
      </Alert>

      <section aria-labelledby="grade-categories-heading">
        <h3 id="grade-categories-heading" className="mb-3 text-lg font-semibold">Category totals</h3>
        {data.categories.length === 0 ? <p className="text-sm text-muted-foreground">No grade categories yet.</p> : (
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
            {data.categories.map((category) => {
              const total = data.categoryTotals.find((item) => item.categoryId === category.id)
              return (
                <Card key={category.id} className="min-w-0 gap-3">
                  <CardHeader><CardTitle className="break-words text-base">{category.name}</CardTitle><CardDescription>{category.weight == null ? 'Points-based' : `${format(category.weight)}% weight`}</CardDescription></CardHeader>
                  <CardContent><div className="text-xl font-semibold">{total?.percentage == null ? '—' : `${format(total.percentage)}%`}</div><div className="mt-1 text-sm text-muted-foreground">{format(total?.pointsEarned)} / {format(total?.pointsPossible)} released points</div></CardContent>
                </Card>
              )
            })}
          </div>
        )}
      </section>

      <section aria-labelledby="grade-items-heading">
        <h3 id="grade-items-heading" className="mb-3 text-lg font-semibold">Grade items</h3>
        {data.items.length === 0 ? (
          <Card><CardContent className="text-sm text-muted-foreground">No grade items have been released yet.</CardContent></Card>
        ) : (
          <ul className="space-y-3">
            {data.items.map((item) => {
              const content = (
                <>
                  <div className="flex min-w-0 flex-wrap items-start justify-between gap-2">
                    <div className="min-w-0"><div className="break-words font-medium">{item.title || 'Unreleased item'}</div>{item.maxPoints != null && <div className="text-sm text-muted-foreground">{format(item.maxPoints)} points possible</div>}</div>
                    <Badge variant={item.status === 'missing' ? 'destructive' : 'outline'}>{statusLabel(item)}</Badge>
                  </div>
                  <div className="mt-3 grid gap-2 text-sm sm:grid-cols-2">
                    <div><span className="text-muted-foreground">Score: </span>{item.status === 'graded' ? `${format(item.pointsEarned)} / ${format(item.maxPoints)}` : statusLabel(item)}</div>
                    <div><span className="text-muted-foreground">Current-total contribution: </span>{item.contributionPercentagePoints == null ? '—' : `${format(item.contributionPercentagePoints)} percentage points`}</div>
                  </div>
                  {item.note && <div className="mt-3 rounded-md bg-muted p-3 text-sm"><span className="font-medium">Feedback: </span>{item.note}</div>}
                </>
              )
              return (
                <li key={item.gradeItemId}>
                  {item.assignmentId ? (
                    <Link to={`/courses/${courseId}/assignments/${item.assignmentId}`} className="block min-w-0 rounded-xl border p-4 hover:bg-muted/40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring">{content}</Link>
                  ) : (
                    <div className="min-w-0 rounded-xl border p-4">{content}</div>
                  )}
                </li>
              )
            })}
          </ul>
        )}
      </section>
    </div>
  )
}
