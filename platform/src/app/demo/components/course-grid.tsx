"use client";

import type { Course, Id } from "@/hooks/use-courses";
import CourseCard from "@/app/demo/components/course-card";
import CourseCardSkeleton from "@/app/demo/components/course-card-skeleton";

export type CourseGridProps = {
  courses: Course[];
  isPending?: boolean;
  onCardClickAction?: (id: Id) => void;
  onEditAction?: (course: Course) => void;
  onCloneAction?: (course: Course) => void;
  onDeleteAction?: (course: Course) => void;
};

export default function CourseGrid({ courses, isPending = false, onCardClickAction, onEditAction, onCloneAction, onDeleteAction }: CourseGridProps) {
  return (
    <div className="flex-1 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-7 mt-6">
      {isPending ? (
        Array.from({ length: 6 }, (_, i) => <CourseCardSkeleton key={i} />)
      ) : courses.length === 0 ? (
        <div className="col-span-full flex flex-col items-center justify-center py-16 h-full">
          <span className="text-lg font-serif text-gray-500">No courses yet. Create one to get started.</span>
        </div>
      ) : (
        courses.map((course) => (
          <CourseCard
            key={course.id}
            course={course}
            onClickAction={onCardClickAction}
            onEditAction={onEditAction}
            onCloneAction={onCloneAction}
            onDeleteAction={onDeleteAction}
          />
        ))
      )}
    </div>
  );
}
