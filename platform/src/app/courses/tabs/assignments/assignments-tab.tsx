import {useState, useEffect} from "react";
import {AssignmentsTable} from "@/app/courses/tabs/assignments/assignments-table";
import {columns, Assignment} from "@/app/courses/tabs/assignments/assignments";
import {CreateAssignmentDialog} from "@/app/courses/tabs/assignments/create-assignment-dialog";
import type { CourseDetail } from "@/hooks/use-courses";

import {useState, useEffect} from "react";
import {AssignmentsTable} from "@/app/courses/tabs/assignments/assignments-table";
import {columns, Assignment} from "@/app/courses/tabs/assignments/assignments";
import {CreateAssignmentDialog} from "@/app/courses/tabs/assignments/create-assignment-dialog";
import {mapAssignments} from "@/app/courses/tabs/assignments/assignment-utils";
import type { CourseDetail } from "@/hooks/use-courses";

export default function AssignmentsTab({
  assignments: rawAssignments = [],
  courseId,
}: {
  assignments?: CourseDetail["assignments"];
  courseId?: string;
}) {
  const [assignments, setAssignments] = useState<Assignment[]>(() => mapAssignments(rawAssignments));

  // Keep local list in sync when parent updates the detailed course data
  useEffect(() => {
    setAssignments(mapAssignments(rawAssignments));
  }, [rawAssignments]);

  const handleAssignmentCreated = (newAssignment: Assignment) => {
    setAssignments(prev => [...prev, newAssignment]);
  };

  return (
    <div>
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-2xl">Assignments</h2>
        <CreateAssignmentDialog 
          courseId={courseId} 
          onAssignmentCreated={handleAssignmentCreated}
        />
      </div>

      <AssignmentsTable columns={columns} data={assignments}/>
    </div>
  );
}