import {use} from "react";

export default function AssignmentPage({params}: { params: Promise<{ id: string }> }) {
  const {id} = use(params);

  return (
    <div className="flex flex-col">
      <div className={"py-2 px-5"}>
        <h1>Assignment Detail Page - {id}</h1>
      </div>
    </div>
  );
}