import { FormEvent, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  GradebookEntryCell,
  GradebookCategory,
  GradebookItem,
  GradebookRow,
  useCourseGradebook,
  useCreateGradebookCategory,
  useCreateGradebookItem,
  useGradingQueue,
  useUpdateGradebookCategory,
  useUpsertGradebookEntry,
} from '@/hooks/use-lms'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Card, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'

const number = new Intl.NumberFormat(undefined, { maximumFractionDigits: 2 })

function formatPoints(value?: number | null) {
  return value === null || value === undefined ? '—' : number.format(value)
}

function formatTotal(total?: GradebookRow['courseTotal']) {
  if (!total) return '—'
  const ratio = `${formatPoints(total.pointsEarned)} / ${formatPoints(total.pointsPossible)}`
  return total.percentage === null || total.percentage === undefined
    ? ratio
    : `${ratio} · ${formatPoints(total.percentage)}%`
}

function entryFor(row: GradebookRow, item: GradebookItem): GradebookEntryCell | undefined {
  return row.itemCells.find((entry) => entry.gradeItemId === item.id)
}

function legacyCellFor(row: GradebookRow, item: GradebookItem) {
  if (item.sourceType !== 'assignment' || !item.sourceId) return undefined
  return row.cells.find((cell) => cell.assignmentId === item.sourceId)
}

function entryLabel(entry?: GradebookEntryCell) {
  if (entry?.status === 'graded') return formatPoints(entry.pointsEarned)
  if (entry?.status === 'excused') return 'Excused'
  if (entry?.status === 'missing') return 'Missing'
  return '—'
}

function AssignmentEntry({ item, row }: { item: GradebookItem; row: GradebookRow }) {
  const entry = entryFor(row, item)
  const legacy = legacyCellFor(row, item)
  const label = entry?.releaseState === 'released'
    ? entryLabel(entry)
    : legacy?.state ?? 'missing'
  const attempts = legacy?.attemptCount ?? 0
  return (
    <>
      <div className="font-medium capitalize">{label}</div>
      <div className="text-xs text-muted-foreground">
        {attempts > 0 ? `${attempts} attempt${attempts === 1 ? '' : 's'}` : 'No attempts'}
        {legacy?.isLate ? ' · late' : ''}
        {entry?.releaseState === 'released' ? ' · released' : ''}
      </div>
    </>
  )
}

function ReadOnlyManualEntry({ item, row }: { item: GradebookItem; row: GradebookRow }) {
  const current = entryFor(row, item)
  return (
    <>
      <div className="font-medium">{entryLabel(current)}</div>
      <div className="text-xs text-muted-foreground">
        {current?.releaseState === 'released' ? 'Released' : 'Not released'}
      </div>
    </>
  )
}

function AddCategoryDialog({ courseId }: { courseId: string }) {
  const mutation = useCreateGradebookCategory(courseId)
  const [open, setOpen] = useState(false)
  const [name, setName] = useState('')
  const [weight, setWeight] = useState('')

  function submit(event: FormEvent) {
    event.preventDefault()
    mutation.mutate(
      { name: name.trim(), weight: weight === '' ? null : Number(weight) },
      {
        onSuccess: () => {
          setName('')
          setWeight('')
          setOpen(false)
        },
      },
    )
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild><Button variant="outline">Add category</Button></DialogTrigger>
      <DialogContent>
        <form onSubmit={submit}>
          <DialogHeader>
            <DialogTitle>Add grade category</DialogTitle>
            <DialogDescription>Weights are percentages. If any category is weighted, configure every category and make the total 100.</DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-5">
            <div className="grid gap-2"><Label htmlFor="category-name">Name</Label><Input id="category-name" value={name} onChange={(event) => setName(event.target.value)} required /></div>
            <div className="grid gap-2"><Label htmlFor="category-weight">Weight (%)</Label><Input id="category-weight" type="number" min="0" step="0.01" value={weight} onChange={(event) => setWeight(event.target.value)} placeholder="Optional" /></div>
          </div>
          <DialogFooter><Button type="submit" disabled={!name.trim() || mutation.isPending}>Create category</Button></DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}

function EditCategoryDialog({ courseId, category }: { courseId: string; category: GradebookCategory }) {
  const mutation = useUpdateGradebookCategory(courseId)
  const [open, setOpen] = useState(false)
  const [name, setName] = useState(category.name)
  const [weight, setWeight] = useState(category.weight?.toString() ?? '')
  const [position, setPosition] = useState(category.position.toString())

  function submit(event: FormEvent) {
    event.preventDefault()
    mutation.mutate(
      {
        categoryId: category.id,
        name: name.trim(),
        weight: weight === '' ? null : Number(weight),
        position: Number(position),
      },
      { onSuccess: () => setOpen(false) },
    )
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild><Button type="button" variant="ghost" size="sm">Edit {category.name}</Button></DialogTrigger>
      <DialogContent>
        <form onSubmit={submit}>
          <DialogHeader>
            <DialogTitle>Edit grade category</DialogTitle>
            <DialogDescription>Weights are percentages. Set every category and total them to 100 for a final weighted total.</DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-5">
            <div className="grid gap-2"><Label htmlFor={`category-name-${category.id}`}>Name</Label><Input id={`category-name-${category.id}`} value={name} onChange={(event) => setName(event.target.value)} required /></div>
            <div className="grid gap-2"><Label htmlFor={`category-weight-${category.id}`}>Weight (%)</Label><Input id={`category-weight-${category.id}`} type="number" min="0" step="0.01" value={weight} onChange={(event) => setWeight(event.target.value)} placeholder="Unweighted" /></div>
            <div className="grid gap-2"><Label htmlFor={`category-position-${category.id}`}>Order</Label><Input id={`category-position-${category.id}`} type="number" min="0" step="1" value={position} onChange={(event) => setPosition(event.target.value)} required /></div>
          </div>
          <DialogFooter><Button type="submit" disabled={!name.trim() || Number(position) < 0 || mutation.isPending}>Save category</Button></DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}

function AddItemDialog({ courseId, categories }: { courseId: string; categories: { id: string; name: string }[] }) {
  const mutation = useCreateGradebookItem(courseId)
  const [open, setOpen] = useState(false)
  const [title, setTitle] = useState('')
  const [maxPoints, setMaxPoints] = useState('100')
  const [categoryId, setCategoryId] = useState('default')

  function submit(event: FormEvent) {
    event.preventDefault()
    mutation.mutate(
      {
        title: title.trim(),
        maxPoints: Number(maxPoints),
        categoryId: categoryId === 'default' ? null : categoryId,
      },
      {
        onSuccess: () => {
          setTitle('')
          setMaxPoints('100')
          setCategoryId('default')
          setOpen(false)
        },
      },
    )
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild><Button>Add manual item</Button></DialogTrigger>
      <DialogContent>
        <form onSubmit={submit}>
          <DialogHeader>
            <DialogTitle>Add manual point item</DialogTitle>
            <DialogDescription>Use for participation, presentations, or other released points not backed by an assignment.</DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-5">
            <div className="grid gap-2"><Label htmlFor="item-title">Title</Label><Input id="item-title" value={title} onChange={(event) => setTitle(event.target.value)} required /></div>
            <div className="grid gap-2"><Label htmlFor="item-points">Maximum points</Label><Input id="item-points" type="number" min="0.01" step="0.01" value={maxPoints} onChange={(event) => setMaxPoints(event.target.value)} required /></div>
            <div className="grid gap-2">
              <Label>Category</Label>
              <Select value={categoryId} onValueChange={setCategoryId}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="default">Default category</SelectItem>
                  {categories.map((category) => <SelectItem key={category.id} value={category.id}>{category.name}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
          </div>
          <DialogFooter><Button type="submit" disabled={!title.trim() || Number(maxPoints) <= 0 || mutation.isPending}>Create item</Button></DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}

function ManualEntryButton({ courseId, item, row }: { courseId: string; item: GradebookItem; row: GradebookRow }) {
  const current = entryFor(row, item)
  const mutation = useUpsertGradebookEntry(courseId)
  const [open, setOpen] = useState(false)
  const [status, setStatus] = useState<'graded' | 'excused' | 'missing'>(
    current?.status === 'excused' || current?.status === 'missing'
      ? current.status
      : 'graded',
  )
  const [points, setPoints] = useState(current?.pointsEarned?.toString() ?? '')

  function submit(event: FormEvent) {
    event.preventDefault()
    mutation.mutate(
      {
        itemId: item.id,
        userId: row.userId,
        status,
        pointsEarned: status === 'graded' ? Number(points) : null,
      },
      { onSuccess: () => setOpen(false) },
    )
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <button type="button" className="w-full rounded px-1 py-1 text-left hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring">
          <div className="font-medium">{entryLabel(current)}</div>
          <div className="text-xs text-muted-foreground">{current ? 'Released' : 'Add points'}</div>
        </button>
      </DialogTrigger>
      <DialogContent>
        <form onSubmit={submit}>
          <DialogHeader><DialogTitle>{item.title}: {row.name}</DialogTitle><DialogDescription>Manual entries are released immediately and count toward server-computed totals.</DialogDescription></DialogHeader>
          <div className="grid gap-4 py-5">
            <div className="grid gap-2"><Label>Status</Label><Select value={status} onValueChange={(value) => setStatus(value as 'graded' | 'excused' | 'missing')}><SelectTrigger><SelectValue /></SelectTrigger><SelectContent><SelectItem value="graded">Graded</SelectItem><SelectItem value="excused">Excused</SelectItem><SelectItem value="missing">Missing</SelectItem></SelectContent></Select></div>
            {status === 'graded' && <div className="grid gap-2"><Label htmlFor={`points-${item.id}-${row.userId}`}>Points (max {formatPoints(item.maxPoints)})</Label><Input id={`points-${item.id}-${row.userId}`} type="number" min="0" max={item.maxPoints} step="0.01" value={points} onChange={(event) => setPoints(event.target.value)} required /></div>}
          </div>
          <DialogFooter><Button type="submit" disabled={mutation.isPending || (status === 'graded' && (points === '' || Number(points) > item.maxPoints))}>Release entry</Button></DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}

export function GradebookTab({ courseId, isArchived = false }: { courseId: string; isArchived?: boolean }) {
  const { data: gradebook, isLoading } = useCourseGradebook(courseId)
  const { data: queue = [] } = useGradingQueue(courseId)
  const orderedCategories = useMemo(() => [...(gradebook?.categories ?? [])].sort((a, b) => a.position - b.position), [gradebook?.categories])
  const orderedItems = useMemo(() => [...(gradebook?.items ?? [])].sort((a, b) => a.position - b.position), [gradebook?.items])

  if (isLoading) return <div className="py-4 text-muted-foreground">Loading gradebook…</div>
  if (!gradebook) return <div className="py-4 text-muted-foreground">Gradebook unavailable.</div>

  const warningReasons = Array.from(new Set(gradebook.rows.flatMap((row) => row.courseTotal?.reasons ?? [])))

  return (
    <div className="space-y-6 py-3">
      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div><h2 className="text-2xl font-semibold">Gradebook</h2><p className="text-sm text-muted-foreground">Released points are canonical. Percentages and weighted totals are computed views.</p></div>
        <div className="flex flex-wrap gap-2"><div className="rounded-md bg-muted px-3 py-2 text-sm font-medium">{queue.length} need{queue.length === 1 ? 's' : ''} grading</div>{isArchived ? <div className="rounded-md border px-3 py-2 text-sm font-medium">Archived · read-only</div> : <><AddCategoryDialog courseId={courseId} /><AddItemDialog courseId={courseId} categories={orderedCategories} /></>}</div>
      </div>

      {warningReasons.length > 0 && <Alert><AlertTitle>Totals are provisional</AlertTitle><AlertDescription>{warningReasons.join(' · ')}. Missing entries are not treated as zero.</AlertDescription></Alert>}

      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
        {orderedCategories.map((category) => {
          const count = orderedItems.filter((item) => item.categoryId === category.id).length
          return <Card key={category.id}><CardHeader className="pb-2"><div className="flex items-start justify-between gap-2"><CardTitle className="text-base">{category.name}</CardTitle>{!isArchived && <EditCategoryDialog courseId={courseId} category={category} />}</div><CardDescription>{category.weight === null || category.weight === undefined ? 'Points-based' : `${formatPoints(category.weight)}% of course`} · {count} item{count === 1 ? '' : 's'}</CardDescription></CardHeader></Card>
        })}
      </div>

      <div className="overflow-x-auto rounded-lg border">
        <table className="w-full text-sm">
          <thead className="bg-muted/50"><tr><th className="sticky left-0 z-10 min-w-52 bg-muted px-3 py-2 text-left">Student</th>{orderedItems.map((item) => <th key={item.id} className="min-w-36 px-3 py-2 text-left"><div>{item.title}</div><div className="text-xs font-normal text-muted-foreground">{formatPoints(item.maxPoints)} pts · {item.isManual ? 'manual' : 'assignment'}</div></th>)}<th className="min-w-48 px-3 py-2 text-left">Course total</th></tr></thead>
          <tbody>
            {gradebook.rows.map((row) => <tr key={row.userId} className="border-t"><td className="sticky left-0 z-10 bg-background px-3 py-2"><div className="font-medium">{row.name}</div><div className="text-xs text-muted-foreground">{row.email}</div></td>{orderedItems.map((item) => <td key={item.id} className="px-3 py-2">{item.isManual ? (isArchived ? <ReadOnlyManualEntry item={item} row={row} /> : <ManualEntryButton courseId={courseId} item={item} row={row} />) : <AssignmentEntry item={item} row={row} />}</td>)}<td className="px-3 py-2"><div className="font-medium">{formatTotal(row.courseTotal)}</div><div className="text-xs text-muted-foreground">{row.courseTotal?.provisional ? 'Provisional' : row.courseTotal?.calculation === 'category_weighted' ? 'Weighted' : 'Points'}</div></td></tr>)}
            {gradebook.rows.length === 0 && <tr><td className="px-3 py-8 text-center text-muted-foreground" colSpan={orderedItems.length + 2}>No active students.</td></tr>}
          </tbody>
        </table>
      </div>

      <div className="space-y-2"><h3 className="text-lg font-semibold">Needs grading</h3>{queue.map((item) => <Link key={item.submissionId} to={`/courses/${courseId}/assignments/${item.assignmentId}`} className="flex items-center justify-between rounded-md border p-3 hover:bg-muted/50"><div><div className="font-medium">{item.studentName}</div><div className="text-sm text-muted-foreground">{item.assignmentTitle} · attempt {item.attemptNumber}</div></div><div className="text-sm capitalize">{item.isLate ? 'Late' : item.status}</div></Link>)}{queue.length === 0 && <p className="text-sm text-muted-foreground">Nothing needs grading.</p>}</div>
    </div>
  )
}
