import { useState } from 'react'
import type { AxiosError } from 'axios'
import { toast } from 'sonner'

import { Button } from '@/components/ui/button'
import { Checkbox } from '@/components/ui/checkbox'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  copyCourse,
  previewCourseCopy,
  saveCourseTemplate,
  type CourseCopyInput,
  type CourseCopyPreview,
  type CourseCopyResult,
  type CourseCopySelection,
} from '@/hooks/use-courses'

const DEFAULT_SELECTION: CourseCopySelection = {
  content: true,
  assignments: true,
  rubrics: true,
  gradebook: true,
  quizzes: true,
  flows: true,
}

const SELECTION_LABELS: Array<{
  key: keyof CourseCopySelection
  label: string
}> = [
  { key: 'content', label: 'Sections and course content' },
  { key: 'assignments', label: 'Assignments' },
  { key: 'rubrics', label: 'Rubrics' },
  { key: 'gradebook', label: 'Gradebook structure' },
  { key: 'quizzes', label: 'Question banks and quizzes' },
  { key: 'flows', label: 'Flow definitions' },
]

function errorDetail(error: unknown, fallback: string): string {
  const detail = (error as AxiosError<{ detail?: string }>)?.response?.data?.detail
  return detail ?? fallback
}

function SummaryGroup({
  label,
  values,
}: {
  label: string
  values: Record<string, number>
}) {
  const entries = Object.entries(values).filter(([, count]) => count > 0)
  if (entries.length === 0) return null

  return (
    <div>
      <p className="font-medium">{label}</p>
      <p className="text-muted-foreground">
        {entries.map(([key, count]) => `${count} ${key.replaceAll('_', ' ')}`).join(', ')}
      </p>
    </div>
  )
}

export function CourseCopyDialog({
  courseId,
  name,
}: {
  courseId: string
  name: string
}) {
  const [open, setOpen] = useState(false)
  const [nextName, setNextName] = useState(`${name} copy`)
  const [datePolicy, setDatePolicy] = useState<'clear' | 'shift'>('clear')
  const [dateShiftDays, setDateShiftDays] = useState(0)
  const [selection, setSelection] = useState<CourseCopySelection>(DEFAULT_SELECTION)
  const [preview, setPreview] = useState<CourseCopyPreview | null>(null)
  const [previewSignature, setPreviewSignature] = useState<string | null>(null)
  const [copyResult, setCopyResult] = useState<CourseCopyResult | null>(null)
  const [busy, setBusy] = useState(false)
  const [idempotencyKey, setIdempotencyKey] = useState('')

  const resetPreview = () => {
    setPreview(null)
    setPreviewSignature(null)
    setCopyResult(null)
    setIdempotencyKey(crypto.randomUUID())
  }

  const request = (): CourseCopyInput => ({
    name: nextName.trim(),
    datePolicy,
    dateShiftDays: datePolicy === 'shift' ? dateShiftDays : 0,
    selection,
    idempotencyKey: idempotencyKey || crypto.randomUUID(),
  })
  const configurationSignature = JSON.stringify({
    name: nextName.trim(),
    datePolicy,
    dateShiftDays: datePolicy === 'shift' ? dateShiftDays : 0,
    selection,
  })
  const hasFreshPreview =
    preview !== null && previewSignature === configurationSignature

  const updateSelection = (key: keyof CourseCopySelection, checked: boolean) => {
    setSelection((current) => {
      const next = { ...current, [key]: checked }
      if (key === 'content' && !checked) next.quizzes = false
      if (key === 'quizzes' && checked) next.content = true
      if (key === 'assignments' && !checked) next.rubrics = false
      if (key === 'rubrics' && checked) next.assignments = true
      return next
    })
    resetPreview()
  }

  const onOpenChange = (nextOpen: boolean) => {
    setOpen(nextOpen)
    if (nextOpen) {
      setPreview(null)
      setPreviewSignature(null)
      setCopyResult(null)
      setIdempotencyKey(crypto.randomUUID())
    }
  }

  const showPreview = async () => {
    setBusy(true)
    try {
      setPreview(await previewCourseCopy(courseId, request()))
      setPreviewSignature(configurationSignature)
    } catch (error) {
      toast.error(errorDetail(error, 'Could not prepare copy preview'))
    } finally {
      setBusy(false)
    }
  }

  const confirm = async () => {
    setBusy(true)
    try {
      const result = await copyCourse(courseId, request())
      setCopyResult(result)
      if (result.status !== 'completed' || !result.destinationCourseId) {
        toast.error(result.errorMessage ?? 'Course copy did not complete')
        return
      }
      toast.success('Draft course copy created')
      setOpen(false)
      window.location.assign(`/courses/${result.destinationCourseId}/content`)
    } catch (error) {
      toast.error(
        errorDetail(
          error,
          'Course copy failed. The failed job was saved and no partial course was kept.',
        ),
      )
    } finally {
      setBusy(false)
    }
  }

  const saveTemplate = async () => {
    setBusy(true)
    try {
      await saveCourseTemplate(courseId, {
        name: nextName.trim(),
        datePolicy,
        dateShiftDays: datePolicy === 'shift' ? dateShiftDays : 0,
        selection,
      })
      toast.success('Private course template saved')
    } catch (error) {
      toast.error(errorDetail(error, 'Could not save template'))
    } finally {
      setBusy(false)
    }
  }

  const valid =
    nextName.trim().length > 0 &&
    Object.values(selection).some(Boolean) &&
    (datePolicy === 'clear' || Number.isInteger(dateShiftDays))

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogTrigger asChild>
        <Button variant="outline">Copy course</Button>
      </DialogTrigger>
      <DialogContent className="max-h-[calc(100dvh-2rem)] overflow-y-auto sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle>Copy course into a new draft</DialogTitle>
          <DialogDescription>
            Choose the authoring material to reuse, review every transformation, then
            create a private draft. Learner work and grades are never copied.
          </DialogDescription>
        </DialogHeader>

        <div className="grid gap-5">
          <div className="grid gap-2">
            <Label htmlFor="course-copy-name">New course or template name</Label>
            <Input
              id="course-copy-name"
              value={nextName}
              onChange={(event) => {
                setNextName(event.target.value)
                resetPreview()
              }}
            />
          </div>

          <fieldset className="grid gap-3">
            <legend className="text-sm font-medium">Include</legend>
            <div className="grid gap-3 sm:grid-cols-2">
              {SELECTION_LABELS.map(({ key, label }) => (
                <div className="flex items-start gap-2" key={key}>
                  <Checkbox
                    id={`course-copy-${key}`}
                    aria-label={label}
                    checked={selection[key]}
                    onCheckedChange={(checked) => {
                      updateSelection(key, checked === true)
                    }}
                  />
                  <Label className="font-normal" htmlFor={`course-copy-${key}`}>
                    {label}
                  </Label>
                </div>
              ))}
            </div>
          </fieldset>

          <div className="grid gap-3 sm:grid-cols-[1fr_10rem]">
            <div className="grid gap-2">
              <Label htmlFor="course-copy-date-policy">Dates</Label>
              <Select
                value={datePolicy}
                onValueChange={(value) => {
                  setDatePolicy(value as 'clear' | 'shift')
                  resetPreview()
                }}
              >
                <SelectTrigger id="course-copy-date-policy">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="clear">Clear all dates</SelectItem>
                  <SelectItem value="shift">Shift all dates</SelectItem>
                </SelectContent>
              </Select>
            </div>
            {datePolicy === 'shift' && (
              <div className="grid gap-2">
                <Label htmlFor="course-copy-shift-days">Shift by days</Label>
                <Input
                  id="course-copy-shift-days"
                  type="number"
                  min={-3650}
                  max={3650}
                  step={1}
                  value={dateShiftDays}
                  onChange={(event) => {
                    setDateShiftDays(event.currentTarget.valueAsNumber)
                    resetPreview()
                  }}
                />
              </div>
            )}
          </div>

          <p className="text-muted-foreground text-sm">
            Always excluded: enrollments, invite codes, submissions, attempts,
            comments, grade entries, notifications, activity, secrets, and execution
            state.
          </p>

          {hasFreshPreview && preview && (
            <div
              aria-label="Course copy preview"
              className="bg-muted/40 grid gap-3 rounded-md border p-4 text-sm"
            >
              <SummaryGroup label="Copy" values={preview.copied} />
              <SummaryGroup label="Transform" values={preview.transformed} />
              <SummaryGroup label="Skip" values={preview.skipped} />
              <SummaryGroup label="Unsupported" values={preview.unsupported} />
              {preview.warnings.length > 0 && (
                <ul className="text-muted-foreground list-disc space-y-1 pl-5">
                  {preview.warnings.map((warning) => (
                    <li key={warning}>{warning}</li>
                  ))}
                </ul>
              )}
              {preview.objects?.length > 0 && (
                <div className="max-h-48 space-y-2 overflow-y-auto border-t pt-3">
                  {preview.objects.map((item) => (
                    <div className="grid grid-cols-[5rem_1fr] gap-2" key={`${item.objectType}-${item.sourceId}`}>
                      <span className="font-medium capitalize">{item.action}</span>
                      <span>
                        {item.title}
                        <span className="text-muted-foreground"> — {item.reason}</span>
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
          {copyResult?.status === 'failed' && (
            <div
              role="alert"
              className="border-destructive/40 bg-destructive/5 text-destructive rounded-md border p-3 text-sm"
            >
              <p className="font-medium">The copy was rolled back safely.</p>
              <p>{copyResult.errorMessage ?? 'No partial course was kept.'}</p>
              <p className="mt-1 text-xs">Job {copyResult.jobId} can be retried.</p>
            </div>
          )}
        </div>

        <DialogFooter>
          <Button
            variant="outline"
            onClick={saveTemplate}
            disabled={busy || !valid}
          >
            Save private template
          </Button>
          {!hasFreshPreview ? (
            <Button onClick={showPreview} disabled={busy || !valid}>
              Preview copy
            </Button>
          ) : (
            <Button onClick={confirm} disabled={busy}>
              {busy
                ? 'Copying…'
                : copyResult?.status === 'failed'
                  ? 'Retry safe copy'
                  : 'Create draft copy'}
            </Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
