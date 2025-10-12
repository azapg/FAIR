import {ColumnDef} from "@tanstack/react-table"
import {
  Ellipsis,
  History,
  Loader,
  ArrowRightLeft,
  Repeat,
  RotateCw,
  Trash,
  SquircleDashed,
  CircleCheck,
  CircleAlert,
  TriangleAlert,
  Circle, BlocksIcon
} from "lucide-react";
import { ReactNode } from "react";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem, DropdownMenuPortal,
  DropdownMenuSeparator, DropdownMenuSub, DropdownMenuSubContent, DropdownMenuSubTrigger,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import {useWorkflowStore, Workflow} from "@/store/workflows-store";
import {RuntimePlugin} from "@/hooks/use-plugins";

export type SubmissionStatus =
  "pending"
  | "submitted"
  | "transcribing"
  | "transcribed"
  | "grading"
  | "graded"
  | "needs_review"
  | "failure"
  | "processing";

export type Submission = {
  id: string;
  name: string;
  status: SubmissionStatus; // simplified
  grade?: number; // TODO: This could be more complex (e.g., letter grade, percentage, etc.).
  feedback?: string;
  submittedAt?: Date;
}

function formatShortDate(date: Date) {
  const months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
  const day = date.getDate().toString().padStart(2, "0");
  const month = months[date.getMonth()];
  const year = date.getFullYear();
  const currentYear = new Date().getFullYear();
  return currentYear === year ? `${day} ${month}` : `${day} ${month} ${year}`;
}

const defaultSize = 14;

const STATUS_META: Record<string, { label: string; color: string; icon?: ReactNode }> = {
  pending: {label: "Pendiente", color: "black", icon: <SquircleDashed size={defaultSize}/>},
  submitted: {label: "Entregado", color: "gray-500", icon: <Circle size={defaultSize}/> },
  transcribing: {label: "Transcribiendo", color: "yellow-500", icon: <Loader className="animate-spin [animation-duration:4.0s]" size={defaultSize}/>},
  transcribed: {label: "Transcrito", color: "blue-500", icon: <CircleCheck size={defaultSize}/>},
  grading: {label: "Calificando", color: "yellow-500", icon: <Loader className="animate-spin [animation-duration:4.0s]" size={defaultSize}/>},
  graded: {label: "Calificado", color: "blue-500", icon: <CircleCheck size={defaultSize}/>},
  needs_review: {label: "Requiere Revisión", color: "orange-500", icon: <CircleAlert size={defaultSize}/>},
  failure: {label: "Error", color: "red-500", icon: <TriangleAlert size={defaultSize}/> },
  processing: {label: "Procesando", color: "yellow-500", icon: <Loader className="animate-spin [animation-duration:4.0s]" size={defaultSize}/>},
};

interface SubmissionStatusLabelProps {
  status: SubmissionStatus | string;
}

export const SubmissionStatusLabel = ({status}: SubmissionStatusLabelProps) => {
  const meta = STATUS_META[status] ?? {label: "Desconocido", color: "gray-500"};

  return (
    <span
      className={`inline-flex items-center justify-center rounded-md border pl-1 pr-1 gap-1 text-sm
        text-${meta.color} bg-${meta.color}/10`}
    >
      {meta.icon}
      <span className="text-foreground">
        {meta.label}
      </span>
    </span>
  );
}

export const columns: ColumnDef<Submission>[] = [
  {
    accessorKey: "name",
    header: "Nombre del Estudiante",
    cell: info => info.getValue(),
  },
  {
    accessorKey: "status",
    header: "Estado",
    cell: info => {
      const status = info.getValue() as SubmissionStatus;
      return <SubmissionStatusLabel status={status}/>;
    }
  },
  {
    accessorKey: "grade",
    header: "Calificación",
    cell: info => {
      const grade = info.getValue();
      return grade !== undefined ? `${grade}/100` : "—";
    }
  },
  {
    accessorKey: "submittedAt",
    header: "Fecha de Entrega",
    cell: info => {
      const date = info.getValue() as Date;
      return date ? formatShortDate(new Date(date)) : "—";
    }
  },
  {
    accessorKey: "feedback",
    header: "Retroalimentación",
    cell: info => {
      const feedback = info.getValue();
      return feedback ? feedback : "—";
    }
  },
  {
    id: "actions",
    cell: info => {
      const submission = info.row.original;

      const workflows = useWorkflowStore(state => state.workflows)
      const activeWorkflow = useWorkflowStore(state => state.drafts[state.activeWorkflowId || ""])

      function runPlugin(plugin?: RuntimePlugin) {
        if (!plugin) return;
        console.log(`Running plugin ${plugin.id}-${plugin.hash}-${plugin.version} on submission ${submission.id} with workflow ${activeWorkflow?.workflowId} and settings`, plugin.settings);
      }

      function runWorkflow(workflow?: Workflow) {
        if (!workflow) return;
        console.log(`Rerunning submission ${submission.id} with workflow ${workflow.id}`, workflow);
      }

      return (
        <DropdownMenu>
          <DropdownMenuTrigger className={"cursor-pointer"}>
            <Ellipsis size={18}/>
          </DropdownMenuTrigger>
          <DropdownMenuContent>
            <DropdownMenuSub>
              <DropdownMenuSubTrigger className={"gap-2"}>
                <BlocksIcon size={16} className={"text-muted-foreground"}/> Run plugin...
              </DropdownMenuSubTrigger>
              <DropdownMenuPortal>
                <DropdownMenuSubContent>
                  {activeWorkflow?.plugins == undefined && (
                    <DropdownMenuItem disabled>No plugins available</DropdownMenuItem>
                  )}

                  {/*TODO: oh my god this is such an ugly code*/}
                  {activeWorkflow && activeWorkflow?.plugins && activeWorkflow?.plugins?.transcriber && (
                    <>
                      <DropdownMenuItem onClick={_ => runPlugin(activeWorkflow.plugins.transcriber)}>{activeWorkflow.plugins.transcriber.settings_schema.title}</DropdownMenuItem>
                      <DropdownMenuSeparator />
                    </>
                  )}

                  {activeWorkflow && activeWorkflow?.plugins && activeWorkflow?.plugins?.grader && (
                    <>
                      <DropdownMenuItem onClick={_ => runPlugin(activeWorkflow.plugins.grader)}>{activeWorkflow.plugins.grader.settings_schema.title}</DropdownMenuItem>
                      <DropdownMenuSeparator />
                    </>
                  )}

                  {activeWorkflow && activeWorkflow?.plugins && activeWorkflow?.plugins?.validator && (
                    <>
                      <DropdownMenuItem onClick={_ => activeWorkflow.plugins.validator}>{activeWorkflow.plugins.validator.settings_schema.title}</DropdownMenuItem>
                      <DropdownMenuSeparator />
                    </>
                  )}

                </DropdownMenuSubContent>
              </DropdownMenuPortal>
            </DropdownMenuSub>
              <DropdownMenuSub>
              <DropdownMenuSubTrigger className={"gap-2"}>
                <ArrowRightLeft size={16} className={"text-muted-foreground"}/> Rerun with...
              </DropdownMenuSubTrigger>
              <DropdownMenuPortal>
                <DropdownMenuSubContent>
                  {workflows?.map(wf => (
                    <DropdownMenuItem key={wf.id} onClick={_ => runWorkflow(wf)}>{wf.name}</DropdownMenuItem>
                  ))}
                  {workflows?.length === 0 && (
                    <DropdownMenuItem disabled>No workflows available</DropdownMenuItem>
                  )}
                </DropdownMenuSubContent>
              </DropdownMenuPortal>
            </DropdownMenuSub>
            {/* TODO: yeah demo code*/}
            <DropdownMenuItem onClick={_ => runWorkflow((workflows || [])[0])}><Repeat /> Rerun</DropdownMenuItem>
            <DropdownMenuItem><History size={16}/> History</DropdownMenuItem>
            <DropdownMenuSeparator/>
            <DropdownMenuItem ><RotateCw size={16}/> Reset</DropdownMenuItem>
            <DropdownMenuItem variant={"destructive"}><Trash size={16}/> Remove</DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      )
    }
  }
]