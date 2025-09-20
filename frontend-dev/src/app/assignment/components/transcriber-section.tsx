"use client"
import SectionContainer from "./section-container"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Button } from "@/components/ui/button"
import {Input} from "@/components/ui/input";

export default function TranscriberSection() {
  
  const onSelectPluginChange = (plugin: string) => {
    console.log("Selected plugin:", plugin);
  }

  return (
    <SectionContainer pluginOptions={["SimpleTranscriber", "ComplexTranscriber"]} onSelectPluginChange={onSelectPluginChange}>
      <div className="flex gap-1 items-center text-xs">
        <label className="text-muted-foreground flex-1">Force Language</label>
        <Select defaultValue="auto">
          <SelectTrigger className="flex-1" size={"sm"}>
            <SelectValue placeholder="auto" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="auto">auto</SelectItem>
            <SelectItem value="en">English</SelectItem>
            <SelectItem value="es">Spanish</SelectItem>
            <SelectItem value="fr">French</SelectItem>
            <SelectItem value="de">German</SelectItem>
            <SelectItem value="zh">Chinese</SelectItem>
            <SelectItem value="ar">Arabic</SelectItem>
          </SelectContent>
        </Select>
      </div>
      <div className="flex gap-1 items-center text-xs">
        <label className="text-muted-foreground w-1/3 flex-1">Max tokens</label>
        <Input className={"flex-1"} type={"number"} max={10000} min={256} defaultValue={2048}/>
      </div>
      <Button variant={"secondary"}>Transcribe all</Button>
    </SectionContainer>
  )
}

