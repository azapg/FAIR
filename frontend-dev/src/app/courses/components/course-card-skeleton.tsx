import { Card, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";

export default function CourseCardSkeleton() {
  return (
    <Card className="h-48 cursor-wait gap-0 overflow-hidden bg-[var(--course-surface)] py-0">
      <CardHeader className="flex flex-1 flex-col items-start gap-3 px-5 pt-5">
        <CardTitle>
          <Skeleton className="h-5 w-32 rounded-md" />
        </CardTitle>
        <CardDescription className="space-y-2 mt-2">
          <Skeleton className="h-3 w-40" />
          <Skeleton className="h-3 w-28" />
        </CardDescription>
      </CardHeader>
      <CardFooter className="border-t border-[var(--line-soft)] bg-[var(--course-surface-muted)] px-5 py-3.5">
        <Skeleton className="h-3 w-24" />
      </CardFooter>
    </Card>
  );
}
