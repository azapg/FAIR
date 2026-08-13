import { useState } from 'react'
import { ArrowDown, ArrowUp, ExternalLink, FileText, LinkIcon, Pencil, Plus, Trash2 } from 'lucide-react'
import { Link } from 'react-router-dom'

import { MarkdownRenderer } from '@/components/markdown-renderer'
import { ArtifactAction } from '@/components/artifact-action'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { LmsArtifact, useArtifacts } from '@/hooks/use-artifacts'
import { Assignment } from '@/hooks/use-assignments'
import {
  CourseItem,
  CourseSection,
  CreateItemInput,
  CreateSectionInput,
  useCourseContent,
  useCreateCourseItem,
  useCreateCourseSection,
  useDeleteCourseItem,
  useDeleteCourseSection,
  useReorderCourseItems,
  useReorderCourseSections,
  useUpdateCourseItem,
  useUpdateCourseSection,
} from '@/hooks/use-course-content'
import { ItemDialog } from './item-dialog'
import { QuizBuilderDialog } from './quiz-builder-dialog'
import { QuizCard } from './quiz-card'
import { SectionDialog } from './section-dialog'


function move<T>(values: T[], index: number, delta: -1 | 1): T[] {
  const target = index + delta
  if (target < 0 || target >= values.length) return values
  const reordered = [...values]
  ;[reordered[index], reordered[target]] = [reordered[target], reordered[index]]
  return reordered
}


function ContentItemView({
  item,
  artifacts,
  canManage,
  isArchived,
}: {
  item: CourseItem
  artifacts: LmsArtifact[]
  canManage: boolean
  isArchived: boolean
}) {
  if (item.kind === 'heading') {
    return <h3 className="text-lg font-semibold">{item.title}</h3>
  }
  if (item.kind === 'page') {
    return (
      <div>
        <h3 className="font-semibold">{item.title}</h3>
        <div className="mt-2 text-sm"><MarkdownRenderer>{String(item.payload.body ?? '')}</MarkdownRenderer></div>
      </div>
    )
  }
  if (item.kind === 'link') {
    return (
      <a className="inline-flex items-center gap-2 font-medium text-primary hover:underline" href={String(item.payload.url ?? '')} target="_blank" rel="noreferrer">
        <LinkIcon className="h-4 w-4" /> {item.title} <ExternalLink className="h-3 w-3" />
      </a>
    )
  }
  if (item.kind === 'file' && item.resourceId) {
    const artifact = artifacts.find((candidate) => candidate.id === item.resourceId) ?? {
      id: item.resourceId,
      title: item.title,
      mime: 'application/octet-stream',
    }
    return (
      <ArtifactAction
        artifact={artifact}
        icon={FileText}
        label={item.title}
        variant="link"
        className="h-auto p-0 font-medium"
      />
    )
  }
  if (item.kind === 'assignment' && item.resourceId) {
    return (
      <Link className="inline-flex items-center gap-2 font-medium text-primary hover:underline" to={`/courses/${item.courseId}/assignments/${item.resourceId}`}>
        <FileText className="h-4 w-4" /> {item.title}
      </Link>
    )
  }
  if (item.kind === 'quiz' && item.resourceId) {
    return (
      <QuizCard
        courseId={item.courseId}
        quizId={item.resourceId}
        canManage={canManage}
        isArchived={isArchived}
      />
    )
  }
  return <span className="font-medium">{item.title}</span>
}


export function CourseContentTab({
  courseId,
  canManage,
  isArchived,
  assignments,
}: {
  courseId: string
  canManage: boolean
  isArchived: boolean
  assignments: Assignment[]
}) {
  const { data: content, isLoading, isError } = useCourseContent(courseId)
  const { data: artifacts = [] } = useArtifacts({ courseId }, canManage)
  const createSection = useCreateCourseSection(courseId)
  const updateSection = useUpdateCourseSection(courseId)
  const deleteSection = useDeleteCourseSection(courseId)
  const reorderSections = useReorderCourseSections(courseId)
  const createItem = useCreateCourseItem(courseId)
  const updateItem = useUpdateCourseItem(courseId)
  const deleteItem = useDeleteCourseItem(courseId)
  const reorderItems = useReorderCourseItems(courseId)

  const [sectionDialogOpen, setSectionDialogOpen] = useState(false)
  const [editingSection, setEditingSection] = useState<CourseSection | null>(null)
  const [itemDialogOpen, setItemDialogOpen] = useState(false)
  const [itemSectionId, setItemSectionId] = useState<string | null>(null)
  const [editingItem, setEditingItem] = useState<CourseItem | null>(null)
  const [quizDialogSectionId, setQuizDialogSectionId] = useState<string | null>(null)

  if (isLoading) return <div className="py-6 text-muted-foreground">Loading course content…</div>
  if (isError || !content) return <div className="py-6 text-muted-foreground">Course content is unavailable.</div>

  const canEdit = canManage && content.canManage && !isArchived
  const openNewSection = () => {
    setEditingSection(null)
    setSectionDialogOpen(true)
  }
  const openNewItem = (sectionId: string) => {
    setItemSectionId(sectionId)
    setEditingItem(null)
    setItemDialogOpen(true)
  }
  const openEditItem = (item: CourseItem) => {
    setItemSectionId(item.sectionId)
    setEditingItem(item)
    setItemDialogOpen(true)
  }

  const saveSection = async (data: CreateSectionInput) => {
    if (editingSection) {
      await updateSection.mutateAsync({ id: editingSection.id, data })
    } else {
      await createSection.mutateAsync(data)
    }
  }

  const saveItem = async (data: CreateItemInput) => {
    if (editingItem) {
      await updateItem.mutateAsync({
        id: editingItem.id,
        data: {
          title: data.title,
          visibility: data.visibility,
          ...(editingItem.kind === 'page' || editingItem.kind === 'link' ? { payload: data.payload } : {}),
        },
      })
    } else if (itemSectionId) {
      await createItem.mutateAsync({ sectionId: itemSectionId, data })
    }
  }

  const moveSection = (index: number, delta: -1 | 1) => {
    const ordered = move(content.sections, index, delta)
    if (ordered !== content.sections) reorderSections.mutate(ordered.map((section) => section.id))
  }

  const moveItem = (section: CourseSection, index: number, delta: -1 | 1) => {
    const ordered = move(section.items, index, delta)
    if (ordered !== section.items) reorderItems.mutate({ sectionId: section.id, orderedIds: ordered.map((item) => item.id) })
  }

  return (
    <div className="space-y-5 py-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-2xl font-semibold">Course content</h2>
          <p className="text-sm text-muted-foreground">
            {content.canManage ? 'Organize pages, links, files, assignments, and quizzes into a student-facing outline.' : 'Work through the course outline in order.'}
          </p>
        </div>
        {canEdit && <Button onClick={openNewSection}><Plus /> Add section</Button>}
      </div>

      {isArchived && content.canManage && (
        <div className="rounded-md border bg-muted/50 p-3 text-sm text-muted-foreground">
          This course is archived. Its content is read-only.
        </div>
      )}

      {content.sections.map((section, sectionIndex) => (
        <section key={section.id} className="rounded-lg border" aria-labelledby={`section-${section.id}`}>
          <div className="flex items-start gap-3 border-b bg-muted/30 p-4">
            <div className="min-w-0 flex-1">
              <div className="flex flex-wrap items-center gap-2">
                <h3 id={`section-${section.id}`} className="text-xl font-semibold">{section.title}</h3>
                {content.canManage && <Badge variant="outline">{section.visibility}</Badge>}
              </div>
              {section.summary && <p className="mt-1 text-sm text-muted-foreground">{section.summary}</p>}
            </div>
            {canEdit && (
              <div className="flex shrink-0 items-center gap-1">
                <Button variant="ghost" size="icon-sm" aria-label={`Move ${section.title} section up`} disabled={sectionIndex === 0 || reorderSections.isPending} onClick={() => moveSection(sectionIndex, -1)}><ArrowUp /></Button>
                <Button variant="ghost" size="icon-sm" aria-label={`Move ${section.title} section down`} disabled={sectionIndex === content.sections.length - 1 || reorderSections.isPending} onClick={() => moveSection(sectionIndex, 1)}><ArrowDown /></Button>
                <Button variant="ghost" size="icon-sm" aria-label={`Edit ${section.title} section`} onClick={() => { setEditingSection(section); setSectionDialogOpen(true) }}><Pencil /></Button>
                <Button
                  variant="ghost"
                  size="icon-sm"
                  aria-label={`Delete ${section.title} section`}
                  onClick={() => {
                    if (window.confirm(`Delete “${section.title}” and all content inside it?`)) deleteSection.mutate(section.id)
                  }}
                ><Trash2 /></Button>
              </div>
            )}
          </div>
          <div className="divide-y">
            {section.items.map((item, itemIndex) => (
              <div key={item.id} className="flex items-start gap-3 p-4">
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-start gap-2">
                    <div className="min-w-0 flex-1">
                      <ContentItemView item={item} artifacts={artifacts} canManage={content.canManage} isArchived={isArchived} />
                    </div>
                    {content.canManage && (
                      <div className="flex gap-1">
                        <Badge variant="secondary">{item.kind}</Badge>
                        <Badge variant="outline">{item.visibility}</Badge>
                      </div>
                    )}
                  </div>
                </div>
                {canEdit && (
                  <div className="flex shrink-0 items-center gap-1">
                    <Button variant="ghost" size="icon-sm" aria-label={`Move ${item.title} up`} disabled={itemIndex === 0 || reorderItems.isPending} onClick={() => moveItem(section, itemIndex, -1)}><ArrowUp /></Button>
                    <Button variant="ghost" size="icon-sm" aria-label={`Move ${item.title} down`} disabled={itemIndex === section.items.length - 1 || reorderItems.isPending} onClick={() => moveItem(section, itemIndex, 1)}><ArrowDown /></Button>
                    <Button variant="ghost" size="icon-sm" aria-label={`Edit ${item.title}`} onClick={() => openEditItem(item)}><Pencil /></Button>
                    <Button
                      variant="ghost"
                      size="icon-sm"
                      aria-label={`Delete ${item.title}`}
                      onClick={() => {
                        if (window.confirm(`Delete “${item.title}”?`)) deleteItem.mutate(item.id)
                      }}
                    ><Trash2 /></Button>
                  </div>
                )}
              </div>
            ))}
            {section.items.length === 0 && (
              <div className="p-6 text-center text-sm text-muted-foreground">No content in this section.</div>
            )}
          </div>
          {canEdit && (
            <div className="flex flex-wrap gap-2 border-t p-3">
              <Button variant="outline" size="sm" onClick={() => openNewItem(section.id)}><Plus /> Add content</Button>
              <Button variant="outline" size="sm" onClick={() => setQuizDialogSectionId(section.id)}><Plus /> Add quiz</Button>
            </div>
          )}
        </section>
      ))}

      {content.sections.length === 0 && (
        <div className="rounded-lg border p-8 text-center text-muted-foreground">
          {canEdit ? 'Add the first section to build this course outline.' : 'No course content has been published yet.'}
        </div>
      )}

      {canManage && (
        <>
          <SectionDialog
            section={editingSection}
            open={sectionDialogOpen}
            onOpenChange={setSectionDialogOpen}
            onSubmit={saveSection}
            pending={createSection.isPending || updateSection.isPending}
          />
          <ItemDialog
            item={editingItem}
            assignments={assignments}
            artifacts={artifacts}
            open={itemDialogOpen}
            onOpenChange={setItemDialogOpen}
            onSubmit={saveItem}
            pending={createItem.isPending || updateItem.isPending}
          />
          {quizDialogSectionId && (
            <QuizBuilderDialog
              courseId={courseId}
              sectionId={quizDialogSectionId}
              open
              onOpenChange={(open) => {
                if (!open) setQuizDialogSectionId(null)
              }}
            />
          )}
        </>
      )}
    </div>
  )
}
