import type { Course } from "@/hooks/use-courses";
import CourseCard from "@/app/courses/components/course-card";
import CourseCardSkeleton from "@/app/courses/components/course-card-skeleton";
import {Alert, AlertDescription, AlertTitle} from "@/components/ui/alert";
import {CircleAlert, BookOpen, ArrowUpRightIcon} from "lucide-react";
import {
  Empty,
  EmptyContent,
  EmptyDescription,
  EmptyHeader,
  EmptyMedia,
  EmptyTitle,
} from "@/components/ui/empty";
import { Button } from "@/components/ui/button";
import { useTranslation } from "react-i18next";

export type CourseGridProps = {
  courses: Course[];
  isPending?: boolean;
  isError?: boolean;
  onCardClickAction?: (id: string) => void;
  onDeleteAction?: (course: Course) => void;
  onCreateCourse?: () => void;
};

export default function CourseGrid({ courses, isPending = false, isError = false, onCardClickAction, onDeleteAction, onCreateCourse }: CourseGridProps) {
  const { t, i18n } = useTranslation();
  const currentLang = i18n.language;

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
        <div className="col-span-full flex items-center justify-center py-16">
          <Empty>
            <EmptyHeader>
              <EmptyMedia variant="icon">
                <BookOpen />
              </EmptyMedia>
              <EmptyTitle>{t("courses.noCourses")}</EmptyTitle>
              <EmptyDescription>
                {t("courses.noCoursesDescription")}
              </EmptyDescription>
            </EmptyHeader>
            <EmptyContent>
              <div className="flex gap-2">
                <Button onClick={onCreateCourse}>
                  {t("courses.createCourse")}
                </Button>
                <Button
                  variant="link"
                  asChild
                  className="text-muted-foreground"
                  size="sm"
                >
                  <a
                    href={`/docs/${currentLang}/courses/`}
                    target="_blank"
                    rel="noreferrer"
                  >
                    {t("common.learnMore")} <ArrowUpRightIcon />
                  </a>
                </Button>
              </div>
            </EmptyContent>
          </Empty>
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
