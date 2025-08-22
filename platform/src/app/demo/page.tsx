"use client";

import {
  Card,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Plus } from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

type Course = {
  id: string;
  title: string;
  description: string;
  color: string;
  instructors: string[];
  assignments: string[];
};

const CourseCardSkeleton = () => (
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

export default function CoursesPage() {
  const router = useRouter();
  const [courses, setCourses] = useState<Course[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    const fetchCourses = async () => {
      try {
        const response = await fetch("/data/courses.json", { cache: "no-store" });

        if (!response.ok) {
          setError(`Failed to fetch courses: ${response.status}`);
          return;
        }

        const data = await response.json();

        if (!cancelled) {
          setCourses(data.courses || []);
          setError(null);
        }
      } catch (err: unknown) {
        if (!cancelled) {
          if (err instanceof Error) {
            setError(err?.message || "Failed to load courses");
          } else {
            setError("An unknown error occurred while loading courses");
          }
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    };

    fetchCourses().then();

    return () => {
      cancelled = true;
    };
  }, []);

  const handleCourseClick = (courseId: string) => {
    router.push(`/demo/assignment?courseId=${courseId}`);
  };

  return (
    <main className="p-5">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-3xl">Your courses</h1>
        <Button>
          <Plus className="mr-2" />
          Create
        </Button>
      </div>

      {error && (
        <div className="text-sm text-red-600 mb-4 p-3 bg-red-50 rounded-md">
          Error: {error}
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-7 mt-6">
        {loading
          ? Array.from({ length: 6 }, (_, i) => <CourseCardSkeleton key={i} />)
          : courses.map((course) => (
              <Card
                key={course.id}
                className={`flex flex-col h-full bg-${course.color}-50 hover:bg-${course.color}-100 transition-colors cursor-pointer`}
                onClick={() => handleCourseClick(course.id)}
              >
                <CardHeader className="flex-1 flex flex-col items-start">
                  <CardTitle>{course.title}</CardTitle>
                  <CardDescription>{course.description}</CardDescription>
                </CardHeader>
                <CardFooter>
                  {course.assignments.length} assignment
                  {course.assignments.length !== 1 ? "s" : ""}.
                </CardFooter>
              </Card>
            ))}
      </div>
    </main>
  );
}
