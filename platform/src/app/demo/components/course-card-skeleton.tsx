"use client";

import { Card, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";

export default function CourseCardSkeleton() {
  return (
    <Card className="bg-gray-50 cursor-wait flex flex-col h-full">
      <CardHeader className="flex-1 flex flex-col items-start">
        <CardTitle>
          <Skeleton className="h-[20px] w-32 rounded-full bg-gray-200" />
        </CardTitle>
        <CardDescription className="space-y-2 mt-2">
          <Skeleton className="h-4 w-40 bg-gray-200" />
          <Skeleton className="h-4 w-28 bg-gray-200" />
        </CardDescription>
      </CardHeader>
      <CardFooter>
        <Skeleton className="h-4 w-24 bg-gray-200" />
      </CardFooter>
    </Card>
  );
}

