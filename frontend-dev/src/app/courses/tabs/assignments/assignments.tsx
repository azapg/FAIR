import {ColumnDef} from "@tanstack/react-table";
import {useMemo} from "react";
import {useTranslation} from "react-i18next";
import {Assignment} from "@/hooks/use-assignments";
import {MarkdownRenderer} from "@/components/markdown-renderer";
import truncate from "markdown-truncate";

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
        if (!value) return <div className="h-full flex items-center"></div>;
        const truncatedValue = truncate(value, { limit: 55, ellipsis: "..." });
        return <div className="h-full flex items-center"><MarkdownRenderer compact>{truncatedValue}</MarkdownRenderer></div>;
      },
      footer: props => props.column.id,
    },
    {
      accessorKey: "deadline",
      header: t("assignments.dueDate"),
      cell: info => {
        const raw = info.getValue() as Date | string | undefined;
        if (!raw) return t("assignments.noDueDate");
        const date = raw instanceof Date ? raw : new Date(raw);
        return isNaN(date.getTime()) ? t("assignments.noDueDate") : date.toLocaleDateString(undefined, {
          day: "2-digit",
          month: "short",
        });
      },
      footer: props => props.column.id,
    },
    {
      accessorKey: "maxGrade",
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
