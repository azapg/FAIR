"use client";

import {useState, FormEvent, useEffect} from "react";
import {AssignmentsTable} from "@/app/demo/courses/[...id]/tabs/assignments/assignments-table";
import {columns, Assignment, Grade} from "@/app/demo/courses/[...id]/tabs/assignments/assignments";
import {Button} from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import {Input} from "@/components/ui/input";
import {Label} from "@/components/ui/label";
import {Textarea} from "@/components/ui/textarea";
import {Plus} from "lucide-react";
import {ScrollArea, ScrollBar} from "@/components/ui/scroll-area";
import type { CourseDetail } from "@/hooks/use-courses";

// Map backend course assignments to local Assignment shape used by the table
function mapAssignments(raw: NonNullable<CourseDetail["assignments"]>): Assignment[] {
  return raw.map(a => {
    const totalPoints: Grade | undefined = a.max_grade
      ? (() => {
          const { type, value } = a.max_grade;
          if (type === "points" || type === "percentage") {
            const num = typeof value === "number" ? value : Number(value);
            return Number.isFinite(num) ? ({ type, value: num } as Grade) : undefined;
          }
          if (type === "letter") {
            return { type: "letter", value: String(value) } as Grade;
          }
          // pass_fail
          return { type: "pass_fail", value: Boolean(value) } as Grade;
        })()
      : undefined;

    return {
      id: String(a.id),
      title: a.title,
      description: a.description ?? undefined,
      dueDate: a.deadline ? new Date(a.deadline) : undefined,
      totalPoints,
      // Backend may not provide these; set to now for display purposes.
      createdAt: new Date(),
      updatedAt: new Date(),
    };
  });
}

export default function AssignmentsTab({
  assignments: rawAssignments = [],
}: {
  assignments?: CourseDetail["assignments"];
}) {
  const [assignments, setAssignments] = useState<Assignment[]>(() => mapAssignments(rawAssignments));

  // Keep local list in sync when parent updates the detailed course data
  useEffect(() => {
    setAssignments(mapAssignments(rawAssignments));
  }, [rawAssignments]);

  const [open, setOpen] = useState(false);
  const [form, setForm] = useState<{
    title: string;
    description: string;
    dueDate: string; // yyyy-mm-dd
    gradeType: Grade["type"] | "";
    gradeValue: string; // number/letter/pass|fail as string
  }>({
    title: "",
    description: "",
    dueDate: "",
    gradeType: "",
    gradeValue: "",
  });

  const resetForm = () =>
    setForm({title: "", description: "", dueDate: "", gradeType: "", gradeValue: ""});

  const handleOpenChange = (next: boolean) => {
    setOpen(next);
    if (!next) resetForm();
  };

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    if (!form.title.trim()) return;

    let totalPoints: Grade | undefined = undefined;
    if (form.gradeType) {
      switch (form.gradeType) {
        case "points":
        case "percentage": {
          const num = Number(form.gradeValue);
          if (!Number.isFinite(num)) break;
          totalPoints = {type: form.gradeType, value: num};
          break;
        }
        case "letter":
          if (form.gradeValue.trim()) {
            totalPoints = {type: "letter", value: form.gradeValue.trim()};
          }
          break;
        case "pass_fail":
          totalPoints = {
            type: "pass_fail",
            value: form.gradeValue === "pass",
          };
          break;
      }
    }

    const id =
      typeof crypto !== "undefined" && "randomUUID" in crypto
        ? crypto.randomUUID()
        : Date.now().toString();

    const now = new Date();
    const newAssignment: Assignment = {
      id,
      title: form.title.trim(),
      description: form.description.trim() || undefined,
      dueDate: form.dueDate ? new Date(form.dueDate) : undefined,
      totalPoints,
      createdAt: now,
      updatedAt: now,
    };

    setAssignments(prev => [...prev, newAssignment]);
    setOpen(false);
    resetForm();
  };

  return (
    <div>
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-2xl">Assignments</h2>
        <Dialog open={open} onOpenChange={handleOpenChange}>
          <DialogTrigger asChild>
            <Button>
              <Plus className="mr-2"/>
              Create
            </Button>
          </DialogTrigger>
          <DialogContent className="sm:max-w-[60%] h-[90%]">
            <DialogHeader>
              <DialogTitle>New Assignment</DialogTitle>
            </DialogHeader>
            <ScrollArea className="h-full w-full">
              <form
                className="grid gap-4"
                onSubmit={handleSubmit}
              >
                <div className="grid gap-2">
                  <Label htmlFor="title">Title</Label>
                  <Input
                    id="title"
                    value={form.title}
                    onChange={e => setForm(f => ({...f, title: e.target.value}))}
                    required
                    placeholder="e.g., Essay 2"
                  />
                </div>

                <div className="grid gap-2">
                  <Label htmlFor="description">Description</Label>
                  <Textarea
                    id="description"
                    value={form.description}
                    onChange={e => setForm(f => ({...f, description: e.target.value}))}
                    placeholder="Brief details..."
                  />
                </div>

                <div className="grid gap-2">
                  <Label htmlFor="due">Due date</Label>
                  <Input
                    id="due"
                    type="date"
                    value={form.dueDate}
                    onChange={e => setForm(f => ({...f, dueDate: e.target.value}))}
                  />
                </div>

                <div className="grid gap-2">
                  <Label htmlFor="gradeType">Grading type</Label>
                  <select
                    id="gradeType"
                    className="w-full rounded-md border px-3 py-2 text-sm"
                    value={form.gradeType}
                    onChange={e =>
                      setForm(f => ({
                        ...f,
                        gradeType: e.target.value as Grade["type"] | "",
                        gradeValue: "",
                      }))
                    }
                  >
                    <option value="">None</option>
                    <option value="points">Points</option>
                    <option value="percentage">Percentage</option>
                    <option value="letter">Letter</option>
                    <option value="pass_fail">Pass/Fail</option>
                  </select>
                </div>

                {form.gradeType === "points" || form.gradeType === "percentage" ? (
                  <div className="grid gap-2">
                    <Label htmlFor="gradeValue">
                      {form.gradeType === "points" ? "Points" : "Percentage"}
                    </Label>
                    <Input
                      id="gradeValue"
                      type="number"
                      step="any"
                      value={form.gradeValue}
                      onChange={e => setForm(f => ({...f, gradeValue: e.target.value}))}
                      placeholder={form.gradeType === "points" ? "e.g., 100" : "e.g., 10"}
                    />
                  </div>
                ) : form.gradeType === "letter" ? (
                  <div className="grid gap-2">
                    <Label htmlFor="gradeLetter">Letter grade</Label>
                    <Input
                      id="gradeLetter"
                      value={form.gradeValue}
                      onChange={e => setForm(f => ({...f, gradeValue: e.target.value}))}
                      placeholder="e.g., A+"
                    />
                  </div>
                ) : form.gradeType === "pass_fail" ? (
                  <div className="grid gap-2">
                    <Label htmlFor="pf">Result</Label>
                    <select
                      id="pf"
                      className="w-full rounded-md border px-3 py-2 text-sm"
                      value={form.gradeValue}
                      onChange={e => setForm(f => ({...f, gradeValue: e.target.value}))}
                    >
                      <option value="">Select</option>
                      <option value="pass">Pass</option>
                      <option value="fail">Fail</option>
                    </select>
                  </div>
                ) : null}

                <DialogFooter>
                  <Button type="submit">Add</Button>
                </DialogFooter>
              </form>

              <ScrollBar />
            </ScrollArea>
          </DialogContent>
        </Dialog>
      </div>

      <AssignmentsTable columns={columns} data={assignments}/>
    </div>
  );
}