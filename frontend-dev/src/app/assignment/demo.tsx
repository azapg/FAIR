import {Button} from "@/components/ui/button";
import {CircleCheck, FileText, Hourglass, Link as LinkIcon, Plus} from "lucide-react";
import {Separator} from "@/components/ui/separator";
import {SubmissionsTable} from "@/app/assignment/components/submissions/submissions-table";
import {columns, Submission} from "@/app/assignment/components/submissions/submissions";
import {SidebarProvider, SidebarTrigger} from "@/components/ui/sidebar";
import {ScrollArea, ScrollBar} from "@/components/ui/scroll-area";
import {BreadcrumbNav} from "@/components/breadcrumb-nav";
import {MarkdownRenderer} from "@/components/markdown-renderer";

type Assignment = {
  name: string;
  description: string;
  submissions: Submission[];
}


const assignment: Assignment = {
  name: "Ejercicios de bucles en C",
  description: `Realizar los siguientes problemas de conversión entre sistemas numéricos. Recuerden también **realizar las operaciones inversas** para _comprobar_ que los problemas están bien hechos.

Problemas:

\\item $(2,403)_{10} = (?)_{2}$
\\item $10001011011_{2} = (?)_{16}$
\\item $3FE2A_{16} = (?)_{10}$
\\item $(6756)_{16} = (?)_{2}$
\\item $B6C8D_{16} = (?)_{2}$

Instrucciones:

1. Harán el problema a mano; no utilizarán ninguna herramienta o apoyo web.
2. Las operaciones y el proceso deben poder verse claramente
3. Colocaran su nombre, cedula y fecha en las hojas en donde desarrollen los problemas.
4. Escanearan las hojas en UN SOLO DOCUMENTO, y lo subirán a UP VIRTUAL para la fecha limite que indique la asignación.`,
  submissions: [
    {
      id: "1",
      name: "Juan Pérez",
      status: "failure",
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
      status: "pending",
      feedback: "Requiere revisión adicional.",
    },
    {
      id: "4",
      name: "Ana Torres",
      status: "submitted",
    },
    {
      id: "5",
      name: "Luis Fernández",
      status: "transcribed",
      grade: 75,
      feedback: "Faltan algunos detalles, pero en general bien.",
      submittedAt: new Date("2025-09-03T14:15:00Z"),
    },
    {
      id: "6",
      name: "Sofía Martínez",
      status: "needs_review",
      grade: 95,
      feedback: "Excelente trabajo, muy bien hecho.",
      submittedAt: new Date("2025-09-04T09:45:00Z"),
    },
    {
      id: "7",
      name: "Pedro Sánchez",
      status: "transcribing",
    },
    {
      id: "8",
      name: "Lucía Ramírez",
      status: "grading",
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

export default function DemoAssignmentPage() {
  return (
    <SidebarProvider className={"flex flex-row m-0 p-0 h-auto overflow-none"}>
      <div className={"w-full h-full overflow-auto break-words"}>
        <div className={"flex flex-row justify-between items-center py-2 px-5"}>
          <BreadcrumbNav baseUrl={"demo"} segments={[{
            label: "Courses",
            slug: "courses"
          }, {
            label: "CH7013-VISUALIZACION DE DATOS I",
            slug: "b7cc83c6-d1f5-4508-86aa-2e5ec7d39705"
          }, {
            label: "Assignments",
            slug: "assignments"
          }, {
            label: assignment.name,
            slug: "ejercicios-de-bucles-en-c"
          }]}/>
          <SidebarTrigger/>
        </div>
        <Separator/>
        <div className={"px-8 pt-5"}>
          <div className={"mb-5"}>
            <h1 className={"text-3xl font-bold pb-1"}>{assignment.name}</h1>
            <MarkdownRenderer className={"text-sm text-muted-foreground"}>{assignment.description}</MarkdownRenderer>

            {/* METADATA */}
            {/* TODO: Make this real components, with real data types and functionalities (links, dates, etc) */}
            <ScrollArea className={"w-full h-auto"}>
              <div className={"flex flex-row gap-1 mt-4 items-center"}>
                <h2 className={"text-muted-foreground mr-4 text-sm"}>Properties</h2>
                <Button variant={"secondary"} size={"sm"}>
                  <CircleCheck/> Completed
                </Button>
                <Button variant={"ghost"} size={"sm"}>
                  <Hourglass/> 03 Sep
                </Button>
                <Button variant={"ghost"} size={"sm"}>
                  <Plus/>
                </Button>
              </div>

              <div className={"flex flex-row gap-1 mt-4 items-center"}>
                <h2 className={"text-muted-foreground mr-4 text-sm"}>Resources</h2>
                <Button variant={"secondary"} size={"sm"}>
                  <LinkIcon/> 💻 BUCLES FOR ¿Qué son y...
                </Button>
                <Button variant={"secondary"} size={"sm"}>
                  <FileText/> ejercicios.docx
                </Button>
                <Button variant={"ghost"} size={"sm"}>
                  <Plus/>
                </Button>
              </div>

              <ScrollBar orientation="horizontal"/>
            </ScrollArea>

          </div>

          <div className={"space-y-5 mb-5"}>
            <h2 className={"text-xl font-semibold mb-3"}>Submissions</h2>
            <SubmissionsTable columns={columns} data={assignment.submissions}/>
          </div>

        </div>
      </div>
    </SidebarProvider>
  );
}