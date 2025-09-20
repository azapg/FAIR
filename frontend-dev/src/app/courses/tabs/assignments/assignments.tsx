import {ColumnDef} from "@tanstack/react-table";

export type Grade = {
  type: "percentage" | "points" | "letter" | "pass_fail";
  value: number | string | boolean;
}

export type Assignment = {
  id: string;
  title: string;
  description?: string;
  dueDate?: Date;
  totalPoints?: Grade;
  createdAt: Date;
  updatedAt: Date;
}

// Form state type for create assignment dialog
export type CreateAssignmentForm = {
  title: string;
  description: string;
  dueDate: string; // yyyy-mm-dd
  gradeType: Grade["type"] | "";
  gradeValue: string; // number/letter/pass|fail as string
}

// Artifact chip type for file uploads
export type ArtifactChip = {
  id?: string | number;
  title: string;
  mime: string;
  artifact_type: string;
  storage_type: "local";
  storage_path: string;
  fileName: string;
  status: "pending" | "uploading" | "uploaded" | "error";
  error?: string;
}


export const columns: ColumnDef<Assignment>[] = [
  {
    accessorKey: "title",
    header: "Assignment",
    cell: info => {
      const value = info.getValue() as string;
      return value.length > 50 ? `${value.substring(0, 50)}...` : value;
    },
    footer: props => props.column.id,
  },
  {
    accessorKey: "description",
    header: "Description",
    cell: info => {
      const value = info.getValue() as string;
      if (!value) return "";
      return value.length > 80 ? `${value.substring(0, 80)}...` : value;
    },
    footer: props => props.column.id,
  },
  {
    accessorKey: "dueDate",
    header: "Due Date",
    cell: info => {
      const raw = info.getValue() as Date | string | undefined;
      if (!raw) return "No due date";
      const date = raw instanceof Date ? raw : new Date(raw);
      return isNaN(date.getTime()) ? "No due date" : date.toLocaleDateString();
    },
    footer: props => props.column.id,
  },
  {
    accessorKey: "totalPoints",
    header: "Total Points",
    cell: info => {
      const grade = info.getValue() as Grade | undefined;
      if (!grade) return "N/A";
      switch (grade.type) {
        case "percentage":
          return `${grade.value}%`;
        case "points":
          return `${grade.value} pts`;
        case "letter":
          return grade.value;
        case "pass_fail":
          return (grade.value as boolean) ? "Pass" : "Fail";
        default:
          return "N/A";
      }
    }
  }
]