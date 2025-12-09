import {ColumnDef} from "@tanstack/react-table";
import {useMemo} from "react";
import {useTranslation} from "react-i18next";
import {Assignment} from "@/hooks/use-assignments";

export type Grade = {
  type: "percentage" | "points" | "letter" | "pass_fail";
  value: number | string | boolean;
}

export type CreateAssignmentForm = {
  title: string;
  description: string;
  dueDate: string; // yyyy-mm-dd
  gradeType: Grade["type"] | "";
  gradeValue: string; // number/letter/pass|fail as string
}

export function useAssignmentColumns(): ColumnDef<Assignment>[] {
  const { t } = useTranslation();
  
  return useMemo(() => [
    {
      accessorKey: "title",
      header: t("assignments.titleLabel"),
      cell: info => {
        const value = info.getValue() as string;
        return value.length > 50 ? `${value.substring(0, 50)}...` : value;
      },
      footer: props => props.column.id,
    },
    {
      accessorKey: "description",
      header: t("assignments.description"),
      cell: info => {
        const value = info.getValue() as string;
        if (!value) return "";
        return value.length > 80 ? `${value.substring(0, 80)}...` : value;
      },
      footer: props => props.column.id,
    },
    {
      accessorKey: "dueDate",
      header: t("assignments.dueDate"),
      cell: info => {
        const raw = info.getValue() as Date | string | undefined;
        if (!raw) return t("assignments.noDueDate");
        const date = raw instanceof Date ? raw : new Date(raw);
        return isNaN(date.getTime()) ? t("assignments.noDueDate") : date.toLocaleDateString();
      },
      footer: props => props.column.id,
    },
    {
      accessorKey: "totalPoints",
      header: t("assignments.totalPoints"),
      cell: info => {
        const grade = info.getValue() as Grade | undefined;
        if (!grade) return t("assignments.na");
        switch (grade.type) {
          case "percentage":
            return `${grade.value}%`;
          case "points":
            return `${grade.value} pts`;
          case "letter":
            return grade.value;
          case "pass_fail":
            return (grade.value as boolean) ? t("assignments.pass") : t("assignments.fail");
          default:
            return t("assignments.na");
        }
      }
    }
  ], [t]);
}