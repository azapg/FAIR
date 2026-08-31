import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import {
  useCreateSubmissionComment,
  useSubmissionComments,
} from '@/hooks/use-communication'

export function SubmissionComments({ submissionId }: { submissionId: string }) {
  const [body, setBody] = useState('')
  const { data: comments = [], isLoading } = useSubmissionComments(submissionId)
  const createComment = useCreateSubmissionComment(submissionId)

  return (
    <div className="space-y-3">
      <p className="text-xs text-muted-foreground">Visible only to this student and course staff.</p>
      {isLoading && <div className="text-sm text-muted-foreground">Loading comments…</div>}
      {comments.map((comment) => (
        <div key={comment.id} className="rounded-md bg-muted p-3 text-sm">
          <div className="font-medium">{comment.authorName}</div>
          <div className="mt-1 whitespace-pre-wrap">{comment.body}</div>
        </div>
      ))}
      <div className="flex gap-2">
        <Input value={body} onChange={(event) => setBody(event.target.value)} placeholder="Write a private comment…" />
        <Button
          variant="outline"
          disabled={!body.trim() || createComment.isPending}
          onClick={() => createComment.mutate(body, { onSuccess: () => setBody('') })}
        >
          Send
        </Button>
      </div>
    </div>
  )
}
