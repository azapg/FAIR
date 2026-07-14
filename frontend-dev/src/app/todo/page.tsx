import { Link } from 'react-router-dom'
import { BreadcrumbNav } from '@/components/breadcrumb-nav'
import { useStudentTodo } from '@/hooks/use-lms'

export default function TodoPage() {
  const { data: items = [], isLoading } = useStudentTodo()
  return (
    <main>
      <div className="px-5 py-2"><BreadcrumbNav segments={[{ label: 'To-do', slug: 'todo' }]} /></div>
      <div className="mx-auto max-w-4xl space-y-4 px-6 py-4">
        <div>
          <h1 className="text-3xl font-semibold">To-do</h1>
          <p className="text-sm text-muted-foreground">Published work that is missing or awaiting grading.</p>
        </div>
        {isLoading && <div className="text-muted-foreground">Loading work…</div>}
        {items.map((item) => (
          <Link
            key={item.assignmentId}
            to={`/courses/${item.courseId}/assignments/${item.assignmentId}`}
            className="block rounded-lg border p-4 transition-colors hover:bg-muted/50"
          >
            <div className="flex items-start justify-between gap-4">
              <div>
                <div className="font-semibold">{item.assignmentTitle}</div>
                <div className="text-sm text-muted-foreground">{item.courseName}</div>
              </div>
              <div className="text-right text-sm">
                <div className="capitalize">{item.state}</div>
                <div className="text-xs text-muted-foreground">
                  {item.deadline ? `Due ${new Date(item.deadline).toLocaleString()}` : 'No deadline'}
                </div>
              </div>
            </div>
          </Link>
        ))}
        {!isLoading && items.length === 0 && (
          <div className="rounded-lg border p-8 text-center text-muted-foreground">You are all caught up.</div>
        )}
      </div>
    </main>
  )
}
