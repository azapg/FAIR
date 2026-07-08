import * as React from "react"
import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import { Attachment, AttachmentMedia, AttachmentContent, AttachmentTitle, AttachmentDescription, AttachmentActions, AttachmentAction } from "@/components/ui/attachment"
import { Plus, Mic, Volume2, Send, Globe, Sparkles, Paperclip, Check, X } from "lucide-react"
import { FolderLibraryIcon } from "hugeicons-react"
import {
  DropdownMenu,
  DropdownMenuTrigger,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuCheckboxItem,
  DropdownMenuSub,
  DropdownMenuSubTrigger,
  DropdownMenuSubContent,
  DropdownMenuPortal,
} from "@/components/ui/dropdown-menu"
import { useCourses } from "@/hooks/use-courses"

const VoiceIcon = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="lucide lucide-audio-lines shrink-0">
    <path d="M2 10v3"/>
    <path d="M6 6v11"/>
    <path d="M10 3v18"/>
    <path d="M14 8v7"/>
    <path d="M18 5v13"/>
    <path d="M22 10v3"/>
  </svg>
)

interface ChatInputProps {
  onSend: (message: string, files: any[]) => void
  disabled?: boolean
  placeholder?: string
}

export function ChatInput({ onSend, disabled, placeholder = "Write a message..." }: ChatInputProps) {
  const [inputValue, setInputValue] = React.useState("")
  const [uploadedFiles, setUploadedFiles] = React.useState<{ name: string; size: string; type: string }[]>([])
  const [isListening, setIsListening] = React.useState(false)
  const [webSearchEnabled, setWebSearchEnabled] = React.useState(true)
  const [selectedCourse, setSelectedCourse] = React.useState<string | null>(null)

  const textareaRef = React.useRef<HTMLTextAreaElement | null>(null)
  const { data: realCourses = [] } = useCourses()

  // Auto-grow textarea
  React.useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto"
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 240)}px`
    }
  }, [inputValue])

  const handleSend = () => {
    if (!inputValue.trim() && uploadedFiles.length === 0) return
    onSend(inputValue, uploadedFiles)
    setInputValue("")
    setUploadedFiles([])
  }

  const handleAttachMockFile = () => {
    const fileOptions = [
      { name: "experiment_results.csv", size: "12 KB", type: "CSV" },
      { name: "model_weights_log.json", size: "8 KB", type: "JSON" },
      { name: "diagnostic_chart.png", size: "512 KB", type: "PNG" }
    ]
    const randomFile = fileOptions[Math.floor(Math.random() * fileOptions.length)]
    setUploadedFiles((prev) => [...prev, randomFile])
  }

  const toggleSpeech = () => {
    if (isListening) {
      setIsListening(false)
      return
    }

    setIsListening(true)
    setTimeout(() => {
      setInputValue("Plot the TB cases and display them.")
      setIsListening(false)
    }, 2500)
  }

  return (
    <div className="w-full">
      {/* Attachment Preview Bar */}
      {uploadedFiles.length > 0 && (
        <div className="flex flex-wrap gap-2 p-2 bg-muted/40 border rounded-2xl mb-2">
          {uploadedFiles.map((file, idx) => (
            <Attachment key={idx}>
              <AttachmentMedia>
                <Paperclip className="w-4 h-4 text-muted-foreground" />
              </AttachmentMedia>
              <AttachmentContent>
                <AttachmentTitle>{file.name}</AttachmentTitle>
                <AttachmentDescription>{file.type} · {file.size}</AttachmentDescription>
              </AttachmentContent>
              <AttachmentActions>
                <AttachmentAction
                  type="button"
                  title="Remove"
                  aria-label="Remove"
                  size="icon-sm"
                  variant="ghost"
                  onClick={() => setUploadedFiles((prev) => prev.filter((_, i) => i !== idx))}
                >
                  <X className="w-4 h-4" />
                </AttachmentAction>
              </AttachmentActions>
            </Attachment>
          ))}
        </div>
      )}

      <div className="bg-card shadow-lg rounded-3xl p-1.5 flex items-end gap-2 relative ring-1 ring-border/50">
        {/* Plus Button Dropdown */}
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button
              variant="ghost"
              size="icon"
              className="rounded-xl hover:bg-muted text-muted-foreground hover:text-foreground cursor-pointer h-9 w-9 shrink-0 mb-0.5"
              disabled={disabled}
            >
              <Plus className="w-4 h-4" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent className="w-56 p-1.5 rounded-xl bg-card border shadow-lg z-50">
            <DropdownMenuItem onClick={handleAttachMockFile} className="rounded-lg cursor-pointer flex items-center gap-2 p-2" disabled={disabled}>
              <Paperclip className="w-4 h-4 text-muted-foreground" />
              <span className="text-xs font-medium">Add files or photos</span>
            </DropdownMenuItem>

            <DropdownMenuSub>
              <DropdownMenuSubTrigger className="rounded-lg cursor-pointer flex items-center gap-2 p-2" disabled={disabled}>
                <FolderLibraryIcon className="w-4 h-4 text-muted-foreground" />
                <span className="text-xs font-medium">Add to course</span>
              </DropdownMenuSubTrigger>
              <DropdownMenuPortal>
                <DropdownMenuSubContent className="w-56 p-1.5 rounded-xl bg-card border shadow-lg z-50">
                  {realCourses.map((course: any) => (
                    <DropdownMenuItem
                      key={course.id}
                      onClick={() => setSelectedCourse(course.name)}
                      className={cn("rounded-lg cursor-pointer flex items-center justify-between p-2 text-xs font-medium", selectedCourse === course.name && "bg-muted")}
                    >
                      <span className="truncate">{course.name}</span>
                      {selectedCourse === course.name && <Check className="w-3.5 h-3.5 text-foreground shrink-0 ml-2" />}
                    </DropdownMenuItem>
                  ))}
                  {realCourses.length === 0 && (
                    <DropdownMenuItem className="text-[10px] text-muted-foreground p-2" disabled>
                      No courses found
                    </DropdownMenuItem>
                  )}
                </DropdownMenuSubContent>
              </DropdownMenuPortal>
            </DropdownMenuSub>

            <DropdownMenuSeparator />

            <DropdownMenuCheckboxItem
              checked={webSearchEnabled}
              onCheckedChange={setWebSearchEnabled}
              className="rounded-lg cursor-pointer flex items-center gap-2 p-2 text-xs font-medium pl-8"
              disabled={disabled}
            >
              <span className="flex items-center gap-2">
                <Globe className="w-4 h-4 text-muted-foreground" />
                <span>Web search</span>
              </span>
            </DropdownMenuCheckboxItem>
          </DropdownMenuContent>
        </DropdownMenu>

        {selectedCourse && (
          <div className="bg-primary/10 border border-primary/20 text-primary rounded-xl px-2.5 py-1 text-[10px] font-bold flex items-center gap-1 shrink-0 mb-1 max-w-[120px] truncate select-none">
            <span className="truncate">{selectedCourse}</span>
            <button onClick={() => setSelectedCourse(null)} className="hover:text-primary-foreground cursor-pointer shrink-0" disabled={disabled}>
              <X className="w-3 h-3" />
            </button>
          </div>
        )}

        {/* Textarea */}
        <textarea
          ref={textareaRef}
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey && !disabled) {
              e.preventDefault()
              handleSend()
            }
          }}
          className="flex-grow bg-transparent border-none px-2 py-2 outline-hidden resize-none min-h-[36px] max-h-[240px] overflow-y-auto text-[15px] text-foreground placeholder:text-muted-foreground align-bottom leading-relaxed custom-scrollbar"
          placeholder={isListening ? "Listening..." : placeholder}
          rows={1}
          disabled={isListening || disabled}
        />

        {/* Actions */}
        <div className="flex items-center gap-1 shrink-0 pb-0.5 pr-0.5">
          
          {/* Dictate Button */}
          <Button
            variant="ghost"
            size="icon"
            onClick={toggleSpeech}
            className={cn(
              "h-9 w-9 rounded-xl hover:bg-muted text-muted-foreground hover:text-foreground cursor-pointer transition-colors",
              isListening && "text-red-500 bg-red-50 hover:bg-red-100"
            )}
            disabled={disabled}
            title="Dictate"
          >
            {isListening ? <Volume2 className="w-4 h-4 animate-pulse" /> : <Mic className="w-4 h-4" />}
          </Button>

          {/* Send or Voice Mode Button */}
          {inputValue.trim().length > 0 || uploadedFiles.length > 0 ? (
            <Button
              className={cn(
                "p-2 h-9 w-9 rounded-xl transition-all flex items-center justify-center shadow-xs cursor-pointer bg-foreground text-background hover:opacity-90 shrink-0"
              )}
              disabled={disabled}
              onClick={handleSend}
            >
              <Send className="w-3.5 h-3.5" />
            </Button>
          ) : (
            <Button
              variant="ghost"
              size="icon"
              className="h-9 w-9 rounded-xl hover:bg-muted text-muted-foreground hover:text-foreground cursor-pointer transition-colors shrink-0"
              onClick={() => alert("Starting voice conversation...")}
              disabled={disabled}
              title="Voice Mode"
            >
              <div className="w-4.5 h-4.5 text-muted-foreground flex items-center justify-center">
                <VoiceIcon />
              </div>
            </Button>
          )}
        </div>
      </div>
    </div>
  )
}
