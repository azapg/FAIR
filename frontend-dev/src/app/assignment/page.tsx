import {useParams} from "react-router-dom";


export default function AssignmentPage() {
  const { assignmentId } = useParams<{ assignmentId: string }>()

  return (
    <div className="flex flex-col">
      <div className={"py-2 px-5"}>
        <h1>Assignment Detail Page - {assignmentId}</h1>
      </div>
    </div>
  );
}