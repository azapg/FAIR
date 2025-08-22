"use client"
import { useState } from "react"
import SectionContainer from "./section-container"
import { Textarea } from "@/components/ui/textarea"
import { Slider } from "@/components/ui/slider"
import { Button } from "@/components/ui/button"

export default function GraderSection() {
  const [temperature, setTemperature] = useState<number>(0.5)

  return (
    <SectionContainer label="Grader">
      <div className="flex flex-col gap-1">
        <label className="text-xs font-medium mb-1">Rubric</label>
        <Textarea
          className="w-full rounded px-3 py-2 text-sm resize-y min-h-[48px] bg-background"
          placeholder="Add rubric or {{rubric-template}}"
        />
      </div>
      <div className="flex flex-col gap-1">
        <div className="flex items-center justify-between">
          <label className="text-xs font-medium mb-1">Temperature</label>
          <span className="text-xs text-muted-foreground ml-2">{temperature.toFixed(2)}</span>
        </div>
        <Slider
          value={[temperature]}
          min={0}
          max={1}
          step={0.01}
          onValueChange={(vals) => setTemperature(vals[0])}
        />
      </div>
      <Button variant={"secondary"}>Grade all</Button>
    </SectionContainer>
  )
}

