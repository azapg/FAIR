import {Assignment, Grade} from "@/app/courses/tabs/assignments/assignments";
import type { CourseDetail } from "@/hooks/use-courses";

// Map backend course assignments to local Assignment shape used by the table
export function mapAssignments(raw: NonNullable<CourseDetail["assignments"]>): Assignment[] {
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