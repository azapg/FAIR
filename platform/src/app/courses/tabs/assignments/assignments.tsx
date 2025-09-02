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

export const columns: ColumnDef<Assignment>[] = [
  {
    accessorKey: "title",
    header: "Assignment",
    cell: info => info.getValue(),
    footer: props => props.column.id,
  },
  {
    accessorKey: "description",
    header: "Description",
    cell: info => info.getValue(),
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