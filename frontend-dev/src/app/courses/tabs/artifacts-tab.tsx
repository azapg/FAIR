import {useMemo} from "react";
import {useTranslation} from "react-i18next";
import {Assignment} from "@/hooks/use-assignments";
import {useArtifacts, useDeleteArtifact} from "@/hooks/use-artifacts";
import {Button} from "@/components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow
} from "@/components/ui/table";

export function ArtifactsTab({
  courseId,
  assignments,
}: {
  courseId?: string;
  assignments: Assignment[];
}) {
  const {t} = useTranslation();
  const {data: artifacts, isLoading, isError, refetch} = useArtifacts(
    courseId ? {courseId} : undefined,
    Boolean(courseId)
  );
  const deleteArtifact = useDeleteArtifact();

  const assignmentNames = useMemo(() => {
    const map = new Map<string, string>();
    assignments?.forEach((a) => map.set(a.id, a.title));
    return map;
  }, [assignments]);

  if (!courseId) {
    return <div className="text-sm text-muted-foreground">{t("artifacts.noCourse")}</div>;
  }

  if (isLoading) {
    return <div>{t("common.loading")}</div>;
  }

  if (isError) {
    return <div>{t("artifacts.errorLoading")}</div>;
  }

  if (!artifacts || artifacts.length === 0) {
    return <div className="text-sm text-muted-foreground">{t("artifacts.empty")}</div>;
  }

  const activeArtifacts = artifacts.filter((artifact) => artifact.status !== "archived");
  const archivedArtifacts = artifacts.filter((artifact) => artifact.status === "archived");

  const handleDelete = async (artifactId: string) => {
    await deleteArtifact.mutateAsync(artifactId);
    await refetch();
  };

  return (
    <div className="space-y-3">
      <h3 className="text-xl font-semibold">{t("artifacts.title")}</h3>
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>{t("assignments.titleLabel")}</TableHead>
            <TableHead>{t("artifacts.assignment")}</TableHead>
            <TableHead>{t("artifacts.status")}</TableHead>
            <TableHead>{t("artifacts.access")}</TableHead>
            <TableHead>{t("artifacts.updated")}</TableHead>
            <TableHead className="text-right">{t("actions.courseActions")}</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {activeArtifacts.length === 0 ? (
            <TableRow>
              <TableCell colSpan={6} className="text-sm text-muted-foreground">
                {t("artifacts.empty")}
              </TableCell>
            </TableRow>
          ) : (
            activeArtifacts.map((artifact) => (
              <TableRow key={artifact.id}>
                <TableCell className="font-medium">{artifact.title}</TableCell>
                <TableCell>
                  {artifact.assignmentId ? assignmentNames.get(artifact.assignmentId) ?? artifact.assignmentId : t("assignments.na")}
                </TableCell>
                <TableCell className="capitalize">{artifact.status}</TableCell>
                <TableCell className="capitalize">{artifact.accessLevel}</TableCell>
                <TableCell>
                  {artifact.updatedAt ? new Date(artifact.updatedAt).toLocaleString() : "—"}
                </TableCell>
                <TableCell className="text-right">
                  <Button variant="ghost" size="sm" onClick={() => handleDelete(artifact.id)}>
                    {t("common.delete")}
                  </Button>
                </TableCell>
              </TableRow>
            ))
          )}
        </TableBody>
      </Table>

      {archivedArtifacts.length > 0 && (
        <div className="space-y-2">
          <h4 className="text-lg font-semibold">{t("artifacts.archivedTitle")}</h4>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>{t("assignments.titleLabel")}</TableHead>
                <TableHead>{t("artifacts.assignment")}</TableHead>
                <TableHead>{t("artifacts.status")}</TableHead>
                <TableHead>{t("artifacts.updated")}</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {archivedArtifacts.map((artifact) => (
                <TableRow key={artifact.id}>
                  <TableCell className="font-medium">{artifact.title}</TableCell>
                  <TableCell>
                    {artifact.assignmentId ? assignmentNames.get(artifact.assignmentId) ?? artifact.assignmentId : t("assignments.na")}
                  </TableCell>
                  <TableCell className="capitalize">{artifact.status}</TableCell>
                  <TableCell>
                    {artifact.updatedAt ? new Date(artifact.updatedAt).toLocaleString() : "—"}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}
    </div>
  );
}
