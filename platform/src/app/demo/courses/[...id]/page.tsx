"use client";

import { use } from "react";
import {useCourse} from "@/hooks/use-courses";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { BreadcrumbNav } from "@/app/demo/components/breadcrumb-nav";
import {Separator} from "@/components/ui/separator";

export default function CourseDetailPage({ params }: { params: Promise<{ id: string[] }> }) {
  const { id } = use(params);
  const [courseId, tab] = id;

  const {isLoading, isError, data: course} = useCourse(courseId, Boolean(courseId));

  if (isLoading) {
    return <div>Loading...</div>;
  }

  if (isError || !course) {
    return <div>Error loading course.</div>;
  }

  const segments = [
    { label: "Courses", slug: "courses" },
    ...(courseId ? [{ label: course?.name ?? "Course", slug: courseId }] : []),
    ...(tab ? [{ label: tab.charAt(0).toUpperCase() + tab.slice(1), slug: tab }] : []),
  ];

  return (
    <div className="flex flex-col">
      <div className={"py-2 px-5"}>
        <BreadcrumbNav baseUrl="demo" segments={segments} />
      </div>
      <Separator />
      <div className={"px-8 py-5"}>
        <h1 className={"text-3xl font-bold pb-1"}>{course?.name}</h1>
        <p className={"text-sm text-muted-foreground"}>{course?.description}</p>
      </div>
      <Tabs defaultValue="overview">
        <TabsList className={"px-8"}>
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="assignments">Assignments</TabsTrigger>
          <TabsTrigger value="participants">Participants</TabsTrigger>
          <TabsTrigger value="runs">Runs</TabsTrigger>
          <TabsTrigger value="artifacts">Artifacts</TabsTrigger>
          <TabsTrigger value="workflows">Workflows</TabsTrigger>
          <TabsTrigger value="plugins">Plugins</TabsTrigger>
        </TabsList>
        <TabsContent value="overview">hi</TabsContent>
        <TabsContent value={"assignments"}>assignments</TabsContent>
      </Tabs>
    </div>
  );
}