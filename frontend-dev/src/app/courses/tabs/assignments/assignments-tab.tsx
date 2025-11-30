import {useState, useEffect} from "react";
import {AssignmentsTable} from "@/app/courses/tabs/assignments/assignments-table";
import {columns} from "@/app/courses/tabs/assignments/assignments";
import {CreateAssignmentDialog} from "@/app/courses/tabs/assignments/create-assignment-dialog";
import {Assignment} from "@/hooks/use-assignments";
import {useTranslation} from "react-i18next";

// TODO: Let's just use react-query here directly to manage assignments state
export default function AssignmentsTab({
  assignments: initialAssignments = [],
  courseId,
}: {
  assignments?: Assignment[];
  courseId?: string;
}) {
  const [assignments, setAssignments] = useState<Assignment[]>(() => initialAssignments);
  const {t} = useTranslation();

  useEffect(() => {
    setAssignments(initialAssignments);
  }, [initialAssignments]);

  const handleAssignmentCreated = (newAssignment: Assignment) => {
    setAssignments(prev => [...prev, newAssignment]);
  };

  return (
    <div>
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-2xl">{t("assignments.title")}</h2>
        <CreateAssignmentDialog 
          courseId={courseId} 
          onAssignmentCreated={handleAssignmentCreated}
        />
      </div>

      <AssignmentsTable columns={columns} data={assignments}/>
    </div>
  );
}