import { useCourseGradebook, useGradingQueue } from '@/hooks/use-lms'
import { Link } from 'react-router-dom'

export function GradebookTab({ courseId }: { courseId: string }) {
  const { data: gradebook, isLoading } = useCourseGradebook(courseId)
  const { data: queue = [] } = useGradingQueue(courseId)

  if (isLoading) return <div className="py-4 text-muted-foreground">Loading gradebook…</div>
  if (!gradebook) return <div className="py-4 text-muted-foreground">Gradebook unavailable.</div>

  return (
    <div className="space-y-4 py-3">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-semibold">Gradebook</h2>
          <p className="text-sm text-muted-foreground">One row per active student; latest attempt shown.</p>
        </div>
        <div className="rounded-md bg-muted px-3 py-2 text-sm font-medium">
          {queue.length} need{queue.length === 1 ? 's' : ''} grading
        </div>
      </div>
      <div className="overflow-x-auto rounded-lg border">
        <table className="w-full text-sm">
          <thead className="bg-muted/50">
            <tr>
              <th className="min-w-52 px-3 py-2 text-left">Student</th>
              {gradebook.assignments.map((assignment) => (
                <th key={assignment.id} className="min-w-36 px-3 py-2 text-left">{assignment.title}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {gradebook.rows.map((row) => (
              <tr key={row.userId} className="border-t">
                <td className="px-3 py-2">
                  <div className="font-medium">{row.name}</div>
                  <div className="text-xs text-muted-foreground">{row.email}</div>
                </td>
                {row.cells.map((cell) => (
                  <td key={cell.assignmentId} className="px-3 py-2">
                    <div className="font-medium capitalize">
                      {cell.state === 'returned' ? cell.score ?? 'Returned' : cell.state}
                    </div>
                    <div className="text-xs text-muted-foreground">
                      {cell.attemptCount > 0 ? `${cell.attemptCount} attempt${cell.attemptCount === 1 ? '' : 's'}` : '—'}
                      {cell.isLate ? ' · late' : ''}
                    </div>
                  </td>
                ))}
              </tr>
            ))}
            {gradebook.rows.length === 0 && (
              <tr><td className="px-3 py-8 text-center text-muted-foreground" colSpan={gradebook.assignments.length + 1}>No active students.</td></tr>
            )}
          </tbody>
        </table>
      </div>
      <div className="space-y-2">
        <h3 className="text-lg font-semibold">Needs grading</h3>
        {queue.map((item) => (
          <Link
            key={item.submissionId}
            to={`/courses/${courseId}/assignments/${item.assignmentId}`}
            className="flex items-center justify-between rounded-md border p-3 hover:bg-muted/50"
          >
            <div>
              <div className="font-medium">{item.studentName}</div>
              <div className="text-sm text-muted-foreground">{item.assignmentTitle} · attempt {item.attemptNumber}</div>
            </div>
            <div className="text-sm capitalize">{item.isLate ? 'Late' : item.status}</div>
          </Link>
        ))}
        {queue.length === 0 && <p className="text-sm text-muted-foreground">Nothing needs grading.</p>}
      </div>
    </div>
  )
}
