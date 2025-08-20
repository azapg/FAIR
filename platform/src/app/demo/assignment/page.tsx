import {Button} from "@/components/ui/button";
import {CircleCheck, FileText, Hourglass, Link as LinkIcon, Plus} from "lucide-react";

import Link from "next/link"

import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator,
} from "@/components/ui/breadcrumb"
import {Separator} from "@/components/ui/separator";
import {SubmissionsTable} from "@/app/demo/assignment/submissions-table";
import {columns, Submission} from "@/app/demo/assignment/submissions";

type Assignment = {
  name: string;
  description: string;
  submissions: Submission[];
}


const assignment: Assignment = {
  name: "Ejercicios de bucles en C",
  description: "Realiza los siguientes ejercicios utilizando bucles en C. Cada ejercicio debe ser implementado en un archivo separado y enviado como parte de tu tarea.",
  submissions: [
    {
      id: "1",
      name: "Juan Pérez",
      status: "submitted",
      grade: 85,
      feedback: "Buen trabajo, pero revisa el ejercicio 3.",
      submittedAt: new Date("2025-09-01T10:00:00Z"),
    },
    {
      id: "2",
      name: "María López",
      status: "graded",
      grade: 90,
      feedback: "Excelente solución, todo correcto.",
      submittedAt: new Date("2025-09-02T12:30:00Z"),
    },
    {
      id: "3",
      name: "Carlos García",
      status: "needs_review",
      feedback: "Requiere revisión adicional.",
    },
    {
      id: "4",
      name: "Ana Torres",
      status: "pending",
    },
    {
      id: "5",
      name: "Luis Fernández",
      status: "submitted",
      grade: 75,
      feedback: "Faltan algunos detalles, pero en general bien.",
      submittedAt: new Date("2025-09-03T14:15:00Z"),
    },
    {
      id: "6",
      name: "Sofía Martínez",
      status: "graded",
      grade: 95,
      feedback: "Excelente trabajo, muy bien hecho.",
      submittedAt: new Date("2025-09-04T09:45:00Z"),
    },
    {
      id: "7",
      name: "Pedro Sánchez",
      status: "pending",
    },
    {
      id: "8",
      name: "Lucía Ramírez",
      status: "submitted",
      grade: 80,
      feedback: "Buen esfuerzo, pero revisa el ejercicio 2.",
      submittedAt: new Date("2025-09-05T11:20:00Z"),
    },
    {
      id: "9",
      name: "Javier Díaz",
      status: "needs_review",
      feedback: "Requiere revisión adicional.",
    },
    {
      id: "10",
      name: "Clara Jiménez",
      status: "graded",
      grade: 88,
      feedback: "Buen trabajo, pero hay algunos errores menores.",
      submittedAt: new Date("2025-09-06T13:05:00Z"),
    },
    {
      id: "11",
      name: "Raúl Herrera",
      status: "pending",
    },
    {
      id: "12",
      name: "Elena Castro",
      status: "submitted",
      grade: 92,
      feedback: "Excelente solución, todo correcto.",
      submittedAt: new Date("2024-09-07T15:30:00Z"),
    }
  ]
}

export function BreadcrumbNav({ className }: { className?: string }) {
  return (
    <Breadcrumb className={className}>
      <BreadcrumbList>
        <BreadcrumbItem>
          <BreadcrumbLink asChild>
            <Link href="/">Home</Link>
          </BreadcrumbLink>
        </BreadcrumbItem>
        <BreadcrumbSeparator />
        <BreadcrumbItem>
          <BreadcrumbLink asChild>
            <Link href="/demo">7014 Programación I</Link>
          </BreadcrumbLink>
        </BreadcrumbItem>
        <BreadcrumbSeparator />
        <BreadcrumbItem>
          <BreadcrumbPage>Asignación I</BreadcrumbPage>
        </BreadcrumbItem>
      </BreadcrumbList>
    </Breadcrumb>
  )
}

export default function AssignmentPage() {
  return (
    <div className={"flex flex-row divide-x-2 h-full m-0"}>
      <div className={"w-3/4 h-full overflow-auto break-words"}>
        <BreadcrumbNav className={"pt-3 pl-5 pb-2"}/>
        <Separator />
        <div className={"pl-5 pr-5 pt-3"}>
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
                <LinkIcon /> 💻 BUCLES FOR ¿Qué son y...
              </Button>
              <Button variant={"secondary"} size={"sm"}>
                <FileText /> ejercicios.docx
              </Button>
              <Button variant={"ghost"} size={"sm"}>
                <Plus />
              </Button>
            </div>

          </div>

          <div className={"space-y-5 mb-5"}>
            <h2 className={"text-xl font-semibold mb-3"}>Submissions</h2>
            <SubmissionsTable columns={columns} data={assignment.submissions} />
          </div>

        </div>
      </div>
      <div className={"sticky w-1/4 p-5 h-full overflow-auto break-words"}>
        sidebar here
      </div>
    </div>
  );
}