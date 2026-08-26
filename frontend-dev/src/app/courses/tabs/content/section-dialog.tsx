import { FormEvent, useEffect, useState } from 'react'

import { Button } from '@/components/ui/button'
import {Dialog, DialogDescription, DialogFooter, DialogHeader, DialogTitle} from '@/components/ui/dialog';
import { ResponsiveDialogContent } from '@/components/ui/responsive-dialog';
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import {
  CourseContentVisibility,
  CourseSection,
  CreateSectionInput,
} from '@/hooks/use-course-content'


export function SectionDialog({
  section,
  open,
  onOpenChange,
  onSubmit,
  pending,
}: {
  section?: CourseSection | null
  open: boolean
  onOpenChange: (open: boolean) => void
  onSubmit: (data: CreateSectionInput) => Promise<void>
  pending: boolean
}) {
  const [title, setTitle] = useState('')
  const [summary, setSummary] = useState('')
  const [visibility, setVisibility] = useState<CourseContentVisibility>('draft')

  useEffect(() => {
    if (!open) return
    setTitle(section?.title ?? '')
    setSummary(section?.summary ?? '')
    setVisibility(section?.visibility ?? 'draft')
  }, [open, section])

  const submit = async (event: FormEvent) => {
    event.preventDefault()
    if (!title.trim()) return
    await onSubmit({ title: title.trim(), summary: summary.trim() || null, visibility })
    onOpenChange(false)
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <ResponsiveDialogContent aria-describedby="section-dialog-description">
        <form className="space-y-4" onSubmit={submit}>
          <DialogHeader>
            <DialogTitle>{section ? 'Edit section' : 'Add section'}</DialogTitle>
            <DialogDescription id="section-dialog-description">
              Sections organize the course outline. Draft and hidden sections are staff-only.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-2">
            <Label htmlFor="section-title">Title</Label>
            <Input id="section-title" value={title} onChange={(event) => setTitle(event.target.value)} autoFocus />
          </div>
          <div className="space-y-2">
            <Label htmlFor="section-summary">Summary</Label>
            <Textarea id="section-summary" value={summary} onChange={(event) => setSummary(event.target.value)} />
          </div>
          <div className="space-y-2">
            <Label htmlFor="section-visibility">Visibility</Label>
            <select
              id="section-visibility"
              className="h-9 w-full rounded-md border bg-background px-3 text-sm"
              value={visibility}
              onChange={(event) => setVisibility(event.target.value as CourseContentVisibility)}
            >
              <option value="draft">Draft</option>
              <option value="published">Published</option>
              <option value="hidden">Hidden</option>
            </select>
          </div>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>Cancel</Button>
            <Button type="submit" disabled={!title.trim() || pending}>
              {pending ? 'Saving…' : 'Save section'}
            </Button>
          </DialogFooter>
        </form>
      </ResponsiveDialogContent>
    </Dialog>
  )
}
