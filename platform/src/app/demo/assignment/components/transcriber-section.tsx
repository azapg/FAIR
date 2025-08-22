"use client"
import SectionContainer from "./section-container"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Button } from "@/components/ui/button"

export default function TranscriberSection() {
  return (
    <SectionContainer label="Transcriber">
      <div className="flex gap-1 items-center text-xs">
        <label className="text-muted-foreground w-1/3">Force Language</label>
        <Select defaultValue="auto">
          <SelectTrigger className="w-2/3" size={"sm"}>
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
      <Button variant={"secondary"}>Transcribe all</Button>
    </SectionContainer>
  )
}

