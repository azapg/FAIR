'use client';
import { ColumnDef } from "@tanstack/react-table"
import { Ellipsis, RefreshCcw, RotateCw, History, Trash, ChevronRight } from "lucide-react";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"

export type Submission = {
  id: string;
  name: string;
  status: "pending" | "submitted" | "graded" | "needs_review";
  grade?: number;
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
      const status = info.getValue();
      switch (status) {
        case "pending":
          return "Pendiente";
        case "submitted":
          return "Entregado";
        case "graded":
          return "Calificado";
        case "needs_review":
          return "Requiere Revisión";
        default:
          return "Desconocido";
      }
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

      console.log(submission.id)

      return (
        <DropdownMenu>
          <DropdownMenuTrigger className={"cursor-pointer"}>
            <Ellipsis size={18}/>
          </DropdownMenuTrigger>
          <DropdownMenuContent>
            <DropdownMenuItem><RefreshCcw size={16} /> Grade with... <ChevronRight size={16} /></DropdownMenuItem>
            <DropdownMenuItem><RotateCw size={16} /> Regrade</DropdownMenuItem>
            <DropdownMenuItem><History size={16} /> History</DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem variant={"destructive"}><Trash size={16} /> Remove</DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      )
    }
  }
]