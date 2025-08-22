"use client"
import { useState } from "react"
import SectionContainer from "./section-container"
import { Slider } from "@/components/ui/slider"
import { Button } from "@/components/ui/button"

export default function ValidatorSection() {
  const [temperature, setTemperature] = useState<number>(0.2)

  return (
    <SectionContainer label="Validator">
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
      <Button variant={"secondary"}>Validate all</Button>
    </SectionContainer>
  )
}

