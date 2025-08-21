'use client';

import {Card, CardDescription, CardFooter, CardHeader, CardTitle} from "@/components/ui/card";
import {Button} from "@/components/ui/button";
import {Skeleton} from "@/components/ui/skeleton";
import {Plus} from "lucide-react";
import {useRouter} from "next/navigation";
import {useEffect, useState} from "react";

type Course = {
  id: string;
  title: string;
  description: string;
  color: string;
  instructors: string[];
  assignments: number;
}

export default function CoursesPage() {
  const router = useRouter();
  const [courses, setCourses] = useState<Course[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const res = await fetch('/data/courses.json', { cache: 'no-store' });
        if (!res.ok) throw new Error(`Status ${res.status}`);
        const json = await res.json();
        if (!cancelled) {
          setCourses(json.courses as Course[]);
          setError(null);
        }
      } catch (e:never) {
        if (!cancelled) setError(e.message || 'Failed to load');
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, []);

  return (
    <main className={"p-5"}>
      <div className={"flex items-center justify-between mb-6"}>
        <h1 className={"text-3xl"}>Your courses</h1>
        <Button>
          <Plus /> Create
        </Button>
      </div>
      {error && <div className="text-sm text-red-600 mb-4">Error: {error}</div>}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-7 mt-6">
        {!loading && courses && courses.map((course) => (
          <Card key={course.id}
                className={`flex flex-col h-full bg-${course.color}-50 hover:bg-${course.color}-100 transition-colors cursor-pointer`}
                onClick={() => router.push(`/demo/assignment`)}
          >
            <CardHeader className={"flex-1 flex flex-col items-start"}>
              <CardTitle>{course.title}</CardTitle>
              <CardDescription>{course.description}</CardDescription>
            </CardHeader>
            <CardFooter>{course.assignments} assignments.</CardFooter>
          </Card>
        ))}
        {loading && [...Array(6)].map((_, i) => (
          <Card key={i} className={"bg-gray-50 cursor-wait flex flex-col h-full"}>
            <CardHeader className={"flex-1 flex flex-col items-start"}>
              <CardTitle>
                <Skeleton className="h-[20px] w-32 rounded-full bg-gray-200" />
              </CardTitle>
              <CardDescription className={"space-y-2 mt-2"}>
                <Skeleton className="h-4 w-40 bg-gray-200" />
                <Skeleton className="h-4 w-28 bg-gray-200" />
              </CardDescription>
            </CardHeader>
            <CardFooter>
              <Skeleton className="h-4 w-24 bg-gray-200" />
            </CardFooter>
          </Card>
        ))}
      </div>
    </main>
  );
}
