"use client";

import { use } from "react";
import {useCourse} from "@/hooks/use-courses";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"

export default function CourseDetailPage({ params }: { params: Promise<{ id: string[] }> }) {
  const { id } = use(params);
  const [courseId, tab] = id;

  const {isLoading, isError, data: course} = useCourse(courseId, Boolean(courseId));

  if (isLoading) {
    return <div>Loading...</div>;
  }

  return (
    <div className="px-8 py-5 flex flex-col gap-5">
      <div>
        <h1 className={"text-3xl font-bold pb-1"}>{course?.name}</h1>
        <p className={"text-sm text-muted-foreground"}>{course?.description}</p>
      </div>
      <Tabs defaultValue="overview">
        <TabsList>
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="participants">Participants</TabsTrigger>
          <TabsTrigger value="runs">Runs</TabsTrigger>
          <TabsTrigger value="artifacts">Artifacts</TabsTrigger>
          <TabsTrigger value="workflows">Workflows</TabsTrigger>
          <TabsTrigger value="plugins">Plugins</TabsTrigger>
        </TabsList>
        <TabsContent value="overview">hi</TabsContent>
      </Tabs>
    </div>
  );
}