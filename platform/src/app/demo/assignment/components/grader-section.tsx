"use client"
import { useState } from "react"
import SectionContainer from "./section-container"
import { Slider } from "@/components/ui/slider"
import { Button } from "@/components/ui/button"
import {
  Table,
  TableBody,
  TableCaption,
  TableCell,
  TableFooter,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import {Select, SelectContent, SelectItem, SelectTrigger, SelectValue} from "@/components/ui/select";
import {Switch} from "@/components/ui/switch";
import {Input} from "@/components/ui/input";

const rubric_items = [
  {
    criterion: "Clarity",
    label: "Clarity of the response",
    weight: "0.3",
  },
  {
    criterion: "Relevance",
    label: "Relevance to the question",
    weight: "0.4",
  },
  {
    criterion: "Accuracy",
    label: "Factual accuracy",
    weight: "0.3",
  }
]

export default function GraderSection() {
  const [temperature, setTemperature] = useState<number>(0.5)

  return (
    <SectionContainer label="Grader">
      <Table className="text-xs text-muted-foreground">
        <TableCaption className={"caption-top text-xs text-left pb-1"}>Structured Rubric</TableCaption>
        {/*<TableCaption className={"text-xs text-right pb-1"}><Button variant={"outline"} size={"sm"}>Add criterion</Button></TableCaption>*/}
        <TableHeader>
          <TableRow>
            <TableHead className="w-[100px]">Criterion</TableHead>
            <TableHead>Label</TableHead>
            <TableHead className="text-right">Weight</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {rubric_items.map((item) => (
            <TableRow key={item.criterion}>
              <TableCell contentEditable={"plaintext-only"} suppressContentEditableWarning>{item.criterion}</TableCell>
              <TableCell contentEditable={"plaintext-only"} suppressContentEditableWarning>{item.label}</TableCell>
              <TableCell contentEditable={"plaintext-only"} suppressContentEditableWarning className="text-right">{item.weight}</TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>

      <div className="flex gap-1 items-center text-xs">
        <label className="text-muted-foreground w-1/3 flex-1">RAG source</label>
        <Select defaultValue="nil">
          <SelectTrigger className="flex-1" size={"sm"}>
            <SelectValue placeholder="nil" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="nil">none</SelectItem>
            <SelectItem value="document.pdf">document.pdf</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <div className="flex gap-1 items-center text-xs">
        <label className="text-muted-foreground w-1/3 flex-1">Attachment</label>
        <Input className={"flex-1"} type={"file"}/>
      </div>

      <div className={"flex gap-1 items-center justify-between text-xs"}>
        <label className={"text-muted-foreground"}>Strict</label>
        <Switch />
      </div>

      <div className="flex gap-1">
        <label className="text-xs text-muted-foreground flex-1">Temperature</label>
        <div className="flex items-center justify-between w-full flex-1">
          <span className="text-xs text-muted-foreground mr-2">{temperature.toFixed(2)}</span>
          <Slider
            value={[temperature]}
            min={0}
            max={1}
            step={0.01}
            onValueChange={(vals) => setTemperature(vals[0])}
          />
        </div>
      </div>
      <Button variant={"secondary"}>Grade all</Button>
    </SectionContainer>
  )
}

