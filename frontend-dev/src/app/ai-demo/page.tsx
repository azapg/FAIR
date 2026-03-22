/**
 * TEMPORARY DEMO PAGE — DELETE BEFORE MERGING
 * Route: /ai-demo
 */
import { Button } from "@/components/ui/button"
import { AiInput } from "@/components/ui/ai-input"
import { AiTextarea } from "@/components/ui/ai-textarea"

export default function AiDemoPage() {
  return (
    <div className="min-h-screen bg-background p-8 space-y-12">
      <div className="max-w-2xl mx-auto space-y-12">
        {/* Banner */}
        <div className="rounded-lg border border-destructive bg-destructive/10 p-4 text-sm text-destructive font-medium">
          ⚠ Temporary demo page — delete this file and its route before merging.
        </div>

        <h1 className="text-2xl font-semibold">AI Glow Components Demo</h1>

        <section className="space-y-4">
          <h2 className="text-lg font-medium">AiInput</h2>
          <AiInput type="text" placeholder="Text input" />
        </section>

        <section className="space-y-4">
          <h2 className="text-lg font-medium">Rubrics dialog — Generate with AI section</h2>
          <div className="space-y-4">
            <AiTextarea
              placeholder="Describe your rubric and the AI will generate it for you..."
              className="min-h-24"
            />
            <div className="flex flex-col items-end">
              <Button variant="secondary" className="w-min">
                Generate
              </Button>
            </div>
          </div>
        </section>
      </div>
    </div>
  )
}
