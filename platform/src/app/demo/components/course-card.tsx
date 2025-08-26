"use client";

import { Card, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from "@/components/ui/dropdown-menu";
import { MoreVertical } from "lucide-react";
import type { Course, Id } from "@/hooks/use-courses";

export type CourseCardProps = {
  course: Course;
  onClickAction?: (id: Id) => void;
  onEditAction?: (course: Course) => void;
  onCloneAction?: (course: Course) => void;
  onDeleteAction?: (course: Course) => void;
};

export default function CourseCard({ course, onClickAction, onEditAction, onCloneAction, onDeleteAction }: CourseCardProps) {
  return (
    <Card
      className="flex flex-col bg-amber-50 hover:bg-amber-100 transition-colors relative cursor-pointer"
      onClick={() => onClickAction?.(course.id)}
    >
      <div className="absolute top-3 right-3 z-10">
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button
              variant="ghost"
              size="icon"
              tabIndex={0}
              aria-label="Course actions"
              onClick={(e) => {
                e.stopPropagation();
              }}
            >
              <MoreVertical className="w-5 h-5" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" onClick={(e) => e.stopPropagation()}>
            <DropdownMenuItem onClick={() => onEditAction?.(course)}>Edit</DropdownMenuItem>
            <DropdownMenuItem onClick={() => onCloneAction?.(course)}>Clone</DropdownMenuItem>
            <DropdownMenuItem className="text-red-600" onClick={() => onDeleteAction?.(course)}>
              Delete
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>

      <CardHeader className="flex-1 flex flex-col items-start">
        <CardTitle>{course.name}</CardTitle>
        {course.description && <CardDescription>{course.description}</CardDescription>}
      </CardHeader>
      <CardFooter>
        {/* TODO: fetch name and number of assignments? seems expensive... */}
        Instructor: {String(course.instructor_id)}
      </CardFooter>
    </Card>
  );
}
