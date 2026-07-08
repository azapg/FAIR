import * as React from "react"
import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import { ChevronLeft, ChevronRight, X, ArrowRight, Pencil } from "lucide-react"

export interface ElicitationData {
  id: string
  questions: {
    id: string
    title: string
    options: { label: string; value: string }[]
  }[]
  resolved?: boolean
  selectedOption?: string
}

interface ElicitationPanelProps {
  elicitation: ElicitationData
  onResolve: (elicitationId: string, value: string) => void
  onSkip?: (elicitationId: string) => void
  onDismiss?: () => void
  className?: string
}

export function ElicitationPanel({
  elicitation,
  onResolve,
  onSkip,
  onDismiss,
  className
}: ElicitationPanelProps) {
  const [currentQuestionIndex, setCurrentQuestionIndex] = React.useState(0)
  const [customInputValue, setCustomInputValue] = React.useState("")
  const [answers, setAnswers] = React.useState<Record<string, string>>({})
  
  if (!elicitation || elicitation.resolved) return null

  const questions = elicitation.questions
  if (!questions || questions.length === 0) return null
  
  const currentQuestion = questions[currentQuestionIndex]

  const handleNext = () => {
    if (currentQuestionIndex < questions.length - 1) {
      setCurrentQuestionIndex(prev => prev + 1)
    }
  }

  const handlePrev = () => {
    if (currentQuestionIndex > 0) {
      setCurrentQuestionIndex(prev => prev - 1)
    }
  }

  const handleAnswer = (value: string) => {
    const newAnswers = { ...answers, [currentQuestion.id]: value }
    setAnswers(newAnswers)
    
    if (currentQuestionIndex < questions.length - 1) {
      setCurrentQuestionIndex(prev => prev + 1)
      setCustomInputValue("")
    } else {
      const formattedAnswers = questions.map(q => `${q.title}\n> ${newAnswers[q.id] || "Skipped"}`).join('\n\n')
      onResolve(elicitation.id, formattedAnswers)
    }
  }

  const handleSkip = () => {
    if (currentQuestionIndex < questions.length - 1) {
      setCurrentQuestionIndex(prev => prev + 1)
      setCustomInputValue("")
    } else {
      if (Object.keys(answers).length === 0) {
        onSkip?.(elicitation.id)
      } else {
        const formattedAnswers = questions.map(q => `${q.title}\n> ${answers[q.id] || "Skipped"}`).join('\n\n')
        onResolve(elicitation.id, formattedAnswers)
      }
    }
  }

  const handleSelectOption = (value: string) => {
    handleAnswer(value)
  }

  const handleCustomSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (customInputValue.trim()) {
      handleAnswer(customInputValue)
    }
  }

  return (
    <div className={cn("bg-card shadow-xl border rounded-2xl p-2.5 text-card-foreground flex flex-col w-full mb-3 select-none", className)}>
      <div className="flex items-start justify-between mb-2 mt-1 px-2">
        <h3 className="text-[14px] font-bold text-foreground max-w-[80%] leading-snug">
          {currentQuestion.title}
        </h3>
        
        <div className="flex items-center gap-1.5 text-[12px] text-muted-foreground font-medium">
          {questions.length > 1 && (
            <div className="flex items-center">
              <button 
                onClick={handlePrev} 
                disabled={currentQuestionIndex === 0}
                className="p-1 hover:text-foreground disabled:opacity-30 transition-colors"
              >
                <ChevronLeft className="w-3.5 h-3.5" />
              </button>
              <span className="min-w-[4ch] text-center">
                {currentQuestionIndex + 1} of {questions.length}
              </span>
              <button 
                onClick={handleNext} 
                disabled={currentQuestionIndex === questions.length - 1}
                className="p-1 hover:text-foreground disabled:opacity-30 transition-colors"
              >
                <ChevronRight className="w-3.5 h-3.5" />
              </button>
            </div>
          )}
          <button onClick={onDismiss} className="p-1 hover:text-foreground transition-colors ml-1">
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      <div className="flex flex-col gap-0.5">
        {currentQuestion.options.map((opt, idx) => (
          <button
            key={opt.value}
            onClick={() => handleSelectOption(opt.label)}
            className="group relative flex items-center w-full p-2.5 rounded-xl hover:bg-muted transition-colors text-left"
          >
            <div className="w-6 h-6 flex items-center justify-center bg-muted text-muted-foreground rounded-md text-[11px] font-bold mr-3 shrink-0">
              {idx + 1}
            </div>
            <span className="text-[14px] flex-1 text-muted-foreground font-medium group-hover:text-foreground transition-colors">
              {opt.label}
            </span>
            <ArrowRight className="w-4 h-4 opacity-0 group-hover:opacity-100 text-muted-foreground transition-all ml-2 shrink-0" />
          </button>
        ))}
        
        <div className="h-[1px] w-full bg-border my-1.5" />
        
        <form onSubmit={handleCustomSubmit} className="flex items-center gap-2 relative">
          <div className="absolute left-3.5 flex items-center justify-center text-muted-foreground pointer-events-none">
            <Pencil className="w-4 h-4" />
          </div>
          <input
            type="text"
            value={customInputValue}
            onChange={(e) => setCustomInputValue(e.target.value)}
            placeholder="Something else..."
            className="flex-1 bg-transparent hover:bg-muted/50 focus:bg-muted transition-colors border-none rounded-xl py-3 pl-10 pr-16 text-[14px] outline-none text-foreground placeholder:text-muted-foreground font-medium"
          />
          <div className="absolute right-2 flex items-center">
            {customInputValue.trim() ? (
              <Button 
                type="submit" 
                size="sm" 
                className="h-7 text-[12px] font-bold rounded-lg px-3"
              >
                Send
              </Button>
            ) : (
              <Button 
                type="button" 
                size="sm" 
                variant="secondary"
                onClick={handleSkip}
                className="h-7 text-[12px] font-bold rounded-lg px-3 border-none shadow-none"
              >
                Skip
              </Button>
            )}
          </div>
        </form>
      </div>
    </div>
  )
}
