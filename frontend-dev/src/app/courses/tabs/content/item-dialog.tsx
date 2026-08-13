import { FormEvent, useEffect, useMemo, useState } from 'react'

import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { LmsArtifact } from '@/hooks/use-artifacts'
import { Assignment } from '@/hooks/use-assignments'
import {
  CourseContentVisibility,
  CourseItem,
  CourseItemKind,
  CreateItemInput,
} from '@/hooks/use-course-content'


export function ItemDialog({
  item,
  assignments,
  artifacts,
  open,
  onOpenChange,
  onSubmit,
  pending,
}: {
  item?: CourseItem | null
  assignments: Assignment[]
  artifacts: LmsArtifact[]
  open: boolean
  onOpenChange: (open: boolean) => void
  onSubmit: (data: CreateItemInput) => Promise<void>
  pending: boolean
}) {
  const [title, setTitle] = useState('')
  const [kind, setKind] = useState<CourseItemKind>('page')
  const [visibility, setVisibility] = useState<CourseContentVisibility>('draft')
  const [body, setBody] = useState('')
  const [url, setUrl] = useState('')
  const [resourceId, setResourceId] = useState('')

  useEffect(() => {
    if (!open) return
    setTitle(item?.title ?? '')
    setKind(item?.kind ?? 'page')
    setVisibility(item?.visibility ?? 'draft')
    setBody(typeof item?.payload.body === 'string' ? item.payload.body : '')
    setUrl(typeof item?.payload.url === 'string' ? item.payload.url : '')
    setResourceId(item?.resourceId ?? '')
  }, [open, item])

  const valid = useMemo(() => {
    if (!title.trim()) return false
    if (kind === 'page') return Boolean(body.trim())
    if (kind === 'link') return /^https?:\/\//i.test(url.trim())
    if (kind === 'file' || kind === 'assignment') return Boolean(resourceId)
    return true
  }, [body, kind, resourceId, title, url])

  const submit = async (event: FormEvent) => {
    event.preventDefault()
    if (!valid) return
    const payload = kind === 'page'
      ? { body: body.trim() }
      : kind === 'link'
        ? { url: url.trim() }
        : {}
    await onSubmit({
      title: title.trim(),
      kind,
      visibility,
      resourceId: resourceId || null,
      payload,
    })
    onOpenChange(false)
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[calc(100dvh-2rem)] overflow-y-auto" aria-describedby="item-dialog-description">
        <form className="space-y-4" onSubmit={submit}>
          <DialogHeader>
            <DialogTitle>{item ? 'Edit content item' : 'Add content item'}</DialogTitle>
            <DialogDescription id="item-dialog-description">
              Add instructions or link an existing course resource. Resource type cannot be changed after creation.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-2">
            <Label htmlFor="item-kind">Type</Label>
            <select
              id="item-kind"
              className="h-9 w-full rounded-md border bg-background px-3 text-sm disabled:opacity-60"
              value={kind}
              disabled={Boolean(item)}
              onChange={(event) => {
                setKind(event.target.value as CourseItemKind)
                setResourceId('')
              }}
            >
              <option value="heading">Heading</option>
              <option value="page">Page</option>
              <option value="link">Link</option>
              <option value="file">Existing file</option>
              <option value="assignment">Existing assignment</option>
            </select>
          </div>
          <div className="space-y-2">
            <Label htmlFor="item-title">Title</Label>
            <Input id="item-title" value={title} onChange={(event) => setTitle(event.target.value)} autoFocus />
          </div>
          {kind === 'page' && (
            <div className="space-y-2">
              <Label htmlFor="item-body">Page content</Label>
              <Textarea id="item-body" className="min-h-36" value={body} onChange={(event) => setBody(event.target.value)} />
            </div>
          )}
          {kind === 'link' && (
            <div className="space-y-2">
              <Label htmlFor="item-url">URL</Label>
              <Input id="item-url" type="url" placeholder="https://example.edu" value={url} onChange={(event) => setUrl(event.target.value)} />
            </div>
          )}
          {kind === 'assignment' && (
            <div className="space-y-2">
              <Label htmlFor="item-assignment">Assignment</Label>
              <select
                id="item-assignment"
                className="h-9 w-full rounded-md border bg-background px-3 text-sm disabled:opacity-60"
                value={resourceId}
                disabled={Boolean(item)}
                onChange={(event) => {
                  const id = event.target.value
                  setResourceId(id)
                  const assignment = assignments.find((candidate) => candidate.id === id)
                  if (assignment && !title.trim()) setTitle(assignment.title)
                }}
              >
                <option value="">Choose an assignment</option>
                {assignments.map((assignment) => <option key={assignment.id} value={assignment.id}>{assignment.title}</option>)}
              </select>
            </div>
          )}
          {kind === 'file' && (
            <div className="space-y-2">
              <Label htmlFor="item-file">File</Label>
              <select
                id="item-file"
                className="h-9 w-full rounded-md border bg-background px-3 text-sm disabled:opacity-60"
                value={resourceId}
                disabled={Boolean(item)}
                onChange={(event) => {
                  const id = event.target.value
                  setResourceId(id)
                  const artifact = artifacts.find((candidate) => candidate.id === id)
                  if (artifact && !title.trim()) setTitle(artifact.title)
                }}
              >
                <option value="">Choose a course-visible file</option>
                {artifacts
                  .filter((artifact) => ['course', 'public'].includes(artifact.accessLevel) && artifact.status !== 'archived')
                  .map((artifact) => <option key={artifact.id} value={artifact.id}>{artifact.title}</option>)}
              </select>
            </div>
          )}
          <div className="space-y-2">
            <Label htmlFor="item-visibility">Visibility</Label>
            <select
              id="item-visibility"
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
            <Button type="submit" disabled={!valid || pending}>{pending ? 'Saving…' : 'Save item'}</Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
