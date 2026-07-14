import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import {
  CoursePost,
  useCoursePosts,
  useCreateCoursePost,
  useCreatePostComment,
  usePostComments,
} from '@/hooks/use-communication'

function PostComments({ post }: { post: CoursePost }) {
  const [body, setBody] = useState('')
  const { data: comments = [] } = usePostComments(post.id)
  const createComment = useCreatePostComment(post.id)
  return (
    <div className="mt-3 space-y-2 border-t pt-3">
      {comments.map((comment) => (
        <div key={comment.id} className="text-sm">
          <span className="font-medium">{comment.authorName}</span>{' '}
          <span className="text-muted-foreground">{comment.body}</span>
        </div>
      ))}
      <div className="flex gap-2">
        <Input value={body} onChange={(event) => setBody(event.target.value)} placeholder="Add a class comment…" />
        <Button
          variant="outline"
          disabled={!body.trim() || createComment.isPending}
          onClick={() => createComment.mutate(body, { onSuccess: () => setBody('') })}
        >
          Comment
        </Button>
      </div>
    </div>
  )
}

export function StreamTab({ courseId, canPost }: { courseId: string; canPost: boolean }) {
  const [title, setTitle] = useState('')
  const [body, setBody] = useState('')
  const { data: posts = [], isLoading } = useCoursePosts(courseId)
  const createPost = useCreateCoursePost(courseId)

  return (
    <div className="mx-auto max-w-3xl space-y-4 py-4">
      {canPost && (
        <div className="space-y-3 rounded-lg border p-4">
          <h2 className="font-semibold">Share with your class</h2>
          <Input value={title} onChange={(event) => setTitle(event.target.value)} placeholder="Title" />
          <textarea
            className="min-h-24 w-full rounded-md border bg-background p-3 text-sm"
            value={body}
            onChange={(event) => setBody(event.target.value)}
            placeholder="Announcement or instructions"
          />
          <Button
            disabled={!title.trim() || createPost.isPending}
            onClick={() => createPost.mutate(
              { title, body, kind: 'announcement' },
              { onSuccess: () => { setTitle(''); setBody('') } },
            )}
          >
            Post
          </Button>
        </div>
      )}
      {isLoading && <div className="text-muted-foreground">Loading class stream…</div>}
      {posts.map((post) => (
        <article key={post.id} className="rounded-lg border p-4">
          <div className="text-xs text-muted-foreground">
            {post.authorName} · {new Date(post.createdAt).toLocaleString()}
          </div>
          <h2 className="mt-1 text-lg font-semibold">{post.title}</h2>
          {post.body && <p className="mt-2 whitespace-pre-wrap text-sm">{post.body}</p>}
          <PostComments post={post} />
        </article>
      ))}
      {!isLoading && posts.length === 0 && (
        <div className="rounded-lg border p-8 text-center text-muted-foreground">Nothing has been posted yet.</div>
      )}
    </div>
  )
}
