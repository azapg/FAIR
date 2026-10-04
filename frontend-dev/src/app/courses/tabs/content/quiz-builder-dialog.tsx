import { FormEvent, useEffect, useMemo, useState } from 'react'
import { toast } from 'sonner'

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
import {
  QuestionKind,
  QuizReleasePolicy,
  useAddQuizQuestion,
  useCreateQuestion,
  useCreateQuestionBank,
  useCreateQuiz,
  useQuestionBanks,
} from '@/hooks/use-quizzes'


export function QuizBuilderDialog({
  courseId,
  sectionId,
  open,
  onOpenChange,
}: {
  courseId: string
  sectionId: string
  open: boolean
  onOpenChange: (open: boolean) => void
}) {
  const { data: banks = [], isLoading: banksLoading } = useQuestionBanks(courseId, open)
  const createBank = useCreateQuestionBank(courseId)
  const createQuestion = useCreateQuestion(courseId)
  const createQuiz = useCreateQuiz(courseId)
  const addQuestion = useAddQuizQuestion(courseId)

  const [bankId, setBankId] = useState('new')
  const [bankName, setBankName] = useState('Course question bank')
  const [quizTitle, setQuizTitle] = useState('')
  const [instructions, setInstructions] = useState('')
  const [questionTitle, setQuestionTitle] = useState('')
  const [prompt, setPrompt] = useState('')
  const [kind, setKind] = useState<QuestionKind>('single_choice')
  const [optionsText, setOptionsText] = useState('Option A\nOption B')
  const [correctIndex, setCorrectIndex] = useState(0)
  const [points, setPoints] = useState(1)
  const [attemptLimit, setAttemptLimit] = useState(1)
  const [releasePolicy, setReleasePolicy] = useState<QuizReleasePolicy>('manual')

  useEffect(() => {
    if (!open) return
    setBankId(banks[0]?.id ?? 'new')
  }, [banks, open])

  const options = useMemo(
    () => kind === 'true_false'
      ? ['True', 'False']
      : optionsText.split('\n').map((option) => option.trim()).filter(Boolean),
    [kind, optionsText],
  )
  const pending = createBank.isPending || createQuestion.isPending || createQuiz.isPending || addQuestion.isPending
  const valid = Boolean(
    quizTitle.trim()
    && questionTitle.trim()
    && prompt.trim()
    && options.length >= 2
    && correctIndex >= 0
    && correctIndex < options.length
    && points > 0
    && attemptLimit > 0
    && (bankId !== 'new' || bankName.trim()),
  )

  const submit = async (event: FormEvent) => {
    event.preventDefault()
    if (!valid) return
    let targetBankId = bankId
    if (targetBankId === 'new') {
      const bank = await createBank.mutateAsync({ name: bankName.trim() })
      targetBankId = bank.id
    }
    const question = await createQuestion.mutateAsync({
      bankId: targetBankId,
      input: {
        title: questionTitle.trim(),
        kind,
        prompt: prompt.trim(),
        options: kind === 'true_false' ? [] : options,
        correctOptionIndex: correctIndex,
        defaultPoints: points,
      },
    })
    const version = question.versions.at(-1)
    if (!version) throw new Error('The question version was not returned')
    const quiz = await createQuiz.mutateAsync({
      sectionId,
      title: quizTitle.trim(),
      instructions: instructions.trim() || null,
      attemptLimit,
      releasePolicy,
    })
    await addQuestion.mutateAsync({
      quizId: quiz.id,
      questionVersionId: version.id,
      points,
    })
    toast.success('Draft quiz created', {
      description: 'Review the question, then publish it from the course outline.',
    })
    onOpenChange(false)
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[calc(100dvh-2rem)] max-w-2xl overflow-y-auto" aria-describedby="quiz-builder-description">
        <form className="space-y-5" onSubmit={submit}>
          <DialogHeader>
            <DialogTitle>Create objective quiz</DialogTitle>
            <DialogDescription id="quiz-builder-description">
              Create a reusable versioned question and a linked draft quiz. Answer keys stay staff-only.
            </DialogDescription>
          </DialogHeader>

          <fieldset className="space-y-3 rounded-md border p-4">
            <legend className="px-1 text-[13px] leading-4 font-medium">Quiz settings</legend>
            <div className="space-y-2">
              <Label htmlFor="quiz-title">Quiz title</Label>
              <Input id="quiz-title" value={quizTitle} onChange={(event) => setQuizTitle(event.target.value)} autoFocus />
            </div>
            <div className="space-y-2">
              <Label htmlFor="quiz-instructions">Instructions</Label>
              <Textarea id="quiz-instructions" value={instructions} onChange={(event) => setInstructions(event.target.value)} />
            </div>
            <div className="grid gap-3 sm:grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor="quiz-attempts">Attempt limit</Label>
                <Input id="quiz-attempts" type="number" min={1} max={100} value={attemptLimit} onChange={(event) => setAttemptLimit(Number(event.target.value))} />
              </div>
              <div className="space-y-2">
                <Label htmlFor="quiz-release">Score release</Label>
                <select id="quiz-release" className="h-9 w-full rounded-md border bg-background px-3 text-sm" value={releasePolicy} onChange={(event) => setReleasePolicy(event.target.value as QuizReleasePolicy)}>
                  <option value="manual">Staff releases score</option>
                  <option value="immediate">Immediately after submission</option>
                </select>
              </div>
            </div>
          </fieldset>

          <fieldset className="space-y-3 rounded-md border p-4">
            <legend className="px-1 text-[13px] leading-4 font-medium">Reusable question</legend>
            <div className="grid gap-3 sm:grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor="quiz-bank">Question bank</Label>
                <select id="quiz-bank" className="h-9 w-full rounded-md border bg-background px-3 text-sm" value={bankId} disabled={banksLoading} onChange={(event) => setBankId(event.target.value)}>
                  {banks.map((bank) => <option key={bank.id} value={bank.id}>{bank.name}</option>)}
                  <option value="new">Create a new bank</option>
                </select>
              </div>
              {bankId === 'new' && (
                <div className="space-y-2">
                  <Label htmlFor="quiz-bank-name">New bank name</Label>
                  <Input id="quiz-bank-name" value={bankName} onChange={(event) => setBankName(event.target.value)} />
                </div>
              )}
            </div>
            <div className="space-y-2">
              <Label htmlFor="quiz-question-title">Question title</Label>
              <Input id="quiz-question-title" value={questionTitle} onChange={(event) => setQuestionTitle(event.target.value)} />
            </div>
            <div className="space-y-2">
              <Label htmlFor="quiz-prompt">Prompt</Label>
              <Textarea id="quiz-prompt" value={prompt} onChange={(event) => setPrompt(event.target.value)} />
            </div>
            <div className="grid gap-3 sm:grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor="quiz-kind">Question type</Label>
                <select id="quiz-kind" className="h-9 w-full rounded-md border bg-background px-3 text-sm" value={kind} onChange={(event) => { setKind(event.target.value as QuestionKind); setCorrectIndex(0) }}>
                  <option value="single_choice">Single choice</option>
                  <option value="true_false">True / false</option>
                </select>
              </div>
              <div className="space-y-2">
                <Label htmlFor="quiz-points">Points</Label>
                <Input id="quiz-points" type="number" min="0.0001" step="0.25" value={points} onChange={(event) => setPoints(Number(event.target.value))} />
              </div>
            </div>
            {kind === 'single_choice' && (
              <div className="space-y-2">
                <Label htmlFor="quiz-options">Options, one per line</Label>
                <Textarea id="quiz-options" value={optionsText} onChange={(event) => { setOptionsText(event.target.value); setCorrectIndex(0) }} />
              </div>
            )}
            <div className="space-y-2">
              <Label htmlFor="quiz-correct">Correct answer</Label>
              <select id="quiz-correct" className="h-9 w-full rounded-md border bg-background px-3 text-sm" value={correctIndex} onChange={(event) => setCorrectIndex(Number(event.target.value))}>
                {options.map((option, index) => <option key={`${option}-${index}`} value={index}>{option}</option>)}
              </select>
            </div>
          </fieldset>

          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>Cancel</Button>
            <Button type="submit" disabled={!valid || pending}>{pending ? 'Creating…' : 'Create draft quiz'}</Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
