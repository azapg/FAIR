import type { Course, Id } from "@/hooks/use-courses";
import CourseCard from "@/app/courses/components/course-card";
import CourseCardSkeleton from "@/app/courses/components/course-card-skeleton";
import {Alert, AlertDescription, AlertTitle} from "@/components/ui/alert";
import {CircleAlert} from "lucide-react";

export type CourseGridProps = {
  courses: Course[];
  isPending?: boolean;
  isError?: boolean;
  onCardClickAction?: (id: Id) => void;
  onDeleteAction?: (course: Course) => void;
};

export default function CourseGrid({ courses, isPending = false, isError = false, onCardClickAction, onDeleteAction }: CourseGridProps) {

  if(isError) return (
    // TODO: proof that i need better error handling. user should know exactly what went wrong
    <Alert variant="destructive" className={"w-full mt-6"}>
      <CircleAlert />
      <AlertTitle>Unable to fetch courses</AlertTitle>
      <AlertDescription>
        There was an error fetching your courses. Possible reasons include:
        <ul className="list-inside list-disc text-sm">
          <li>The backend server may be down or unreachable.</li>
          <li>There was an unexpected error processing your request.</li>
          <li>You may not be authenticated. Please log in and try again.</li>
        </ul>
      </AlertDescription>
    </Alert>
  )

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-7 mt-6">
      {isPending ? (
        Array.from({ length: 6 }, (_, i) => <CourseCardSkeleton key={i} />)
      ) : courses.length === 0 && !isError ? (
        <div className="col-span-full flex flex-col items-center justify-center py-16 h-full">
          <span className="text-lg font-serif text-gray-500">No courses yet. Create one to get started.</span>
        </div>
      ) : (
        courses.map((course) => (
          <CourseCard
            key={course.id}
            course={course}
            onClickAction={onCardClickAction}
            onDeleteAction={onDeleteAction}
          />
        ))
      )}
    </div>
  );
}
