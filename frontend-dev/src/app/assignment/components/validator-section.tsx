import { useState } from "react"
import SectionContainer from "./section-container"
import { Slider } from "@/components/ui/slider"
import { Button } from "@/components/ui/button"
import {Textarea} from "@/components/ui/textarea";

export default function ValidatorSection() {
  const [temperature, setTemperature] = useState<number>(0.2)

  return (
    <SectionContainer selectedPlugin="SimpleValidator" pluginOptions={["SimpleValidator", "AdvancedValidator"]}>
      <div className="flex gap-1">
        <div className="flex items-center justify-between">
          <label className="text-xs text-muted-foreground">Temperature</label>
        </div>
        <span className="text-xs text-muted-foreground ml-2">{temperature.toFixed(2)}</span>
        <Slider
          value={[temperature]}
          min={0}
          max={1}
          step={0.01}
          onValueChange={(vals) => setTemperature(vals[0])}
        />
      </div>
      <div className="flex flex-col gap-1">
        <label className="text-xs text-muted-foreground mb-1">Instructions</label>
        <Textarea
          className="w-full rounded px-3 py-2 text-sm resize-y min-h-[48px] bg-background"
          placeholder="Your validation instructions here..."
        />
      </div>

      <Button variant={"secondary"}>Validate all</Button>
    </SectionContainer>
  )
}
