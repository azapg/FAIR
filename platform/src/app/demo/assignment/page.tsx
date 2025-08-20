import {Button} from "@/components/ui/button";
import {CircleCheck, FileText, Hourglass, Link, Plus} from "lucide-react";

type AssignmentSubmissions = {

}

type Assignment = {
  name: string;
  description: string;
  submissions: AssignmentSubmissions[];
}


const assignment: Assignment = {
  name: "Ejercicios de bucles en C",
  description: "Realiza los siguientes ejercicios utilizando bucles en C. Cada ejercicio debe ser implementado en un archivo separado y enviado como parte de tu tarea.",
  submissions: []
}

export default function AssignmentPage() {
  return (
    <div className={"flex flex-row divide-x-2 h-full m-0"}>
      <div className={"w-3/4 p-5 h-full overflow-auto break-words"}>
        <div className={"mb-5"}>
          <h1 className={"text-2xl font-bold"}>{assignment.name}</h1>
          <p>{assignment.description}</p>

          {/* METADATA */}
          {/* TODO: Make this real components, with real data types and functionalities (links, dates, etc) */}

          <div className={"flex flex-row gap-1 mt-4 items-center"}>
            <h2 className={"text-muted-foreground mr-4 text-sm"}>Properties</h2>
            <Button variant={"secondary"} size={"sm"}>
              <CircleCheck /> Completed
            </Button>
            <Button variant={"ghost"} size={"sm"}>
              <Hourglass /> 03 Sep
            </Button>
            <Button variant={"ghost"} size={"sm"}>
              <Plus />
            </Button>
          </div>

          <div className={"flex flex-row gap-1 mt-4 items-center"}>
            <h2 className={"text-muted-foreground mr-4 text-sm"}>Resources</h2>
            <Button variant={"secondary"} size={"sm"}>
              <Link /> 💻 BUCLES FOR ¿Qué son y...
            </Button>
            <Button variant={"secondary"} size={"sm"}>
              <FileText /> ejercicios.docx
            </Button>
            <Button variant={"ghost"} size={"sm"}>
              <Plus />
            </Button>
          </div>

        </div>
        <h2 className={"text-xl font-semibold mt-4"}>Submissions</h2>
      </div>
      <div className={"sticky w-1/4 p-5 h-full overflow-auto break-words"}>
        sidebar here
      </div>
    </div>
  );
}