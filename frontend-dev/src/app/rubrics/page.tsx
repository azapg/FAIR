import { useMemo, useState } from "react";
import { Pencil, Trash2 } from "lucide-react";
import { useTranslation } from "react-i18next";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Rubric,
  useDeleteRubric,
  useRubrics,
} from "@/hooks/use-rubrics";

import { normalizeContent } from "./utils";
import { RubricMatrixView } from "./components/rubric-matrix-view";
import { RubricFormDialog } from "./components/rubric-form-dialog";

export default function RubricsPage() {
  const { t } = useTranslation();
  const { data: rubrics = [], isLoading } = useRubrics();
  const deleteRubric = useDeleteRubric();

  const [selectedRubric, setSelectedRubric] = useState<Rubric | null>(null);
  const [showCreate, setShowCreate] = useState(false);
  const [editRubric, setEditRubric] = useState<Rubric | null>(null);

  const rows = useMemo(() => rubrics, [rubrics]);

  return (
    <div className="p-6 md:p-8 space-y-4">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">
            {t("rubrics.title")}
          </h1>
          <p className="text-sm text-muted-foreground">
            {t("rubrics.subtitle")}
          </p>
        </div>
        <Button onClick={() => setShowCreate(true)}>
          {t("rubrics.createAction")}
        </Button>
      </div>

      <div className="rounded-lg border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>{t("rubrics.columns.name")}</TableHead>
              <TableHead>{t("rubrics.columns.criteria")}</TableHead>
              <TableHead>{t("rubrics.columns.levels")}</TableHead>
              <TableHead>{t("rubrics.columns.created")}</TableHead>
              <TableHead>{t("rubrics.columns.actions")}</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading ? (
              <TableRow>
                <TableCell colSpan={5}>{t("common.loading")}</TableCell>
              </TableRow>
            ) : rows.length === 0 ? (
              <TableRow>
                <TableCell colSpan={5}>{t("rubrics.empty")}</TableCell>
              </TableRow>
            ) : (
              rows.map((rubric) => (
                <TableRow
                  key={rubric.id}
                  className="cursor-pointer"
                  onClick={() => setSelectedRubric(rubric)}
                >
                  <TableCell>{rubric.name}</TableCell>
                  <TableCell>{rubric.content.criteria.length}</TableCell>
                  <TableCell>{rubric.content.levels.length}</TableCell>
                  <TableCell>
                    {new Date(rubric.createdAt).toLocaleDateString()}
                  </TableCell>
                  <TableCell>
                    <div className="flex items-center gap-2">
                      <Button
                        size="icon"
                        variant="ghost"
                        onClick={(event) => {
                          event.stopPropagation();
                          setEditRubric(rubric);
                        }}
                      >
                        <Pencil className="h-4 w-4" />
                      </Button>
                      <Button
                        size="icon"
                        variant="ghost"
                        onClick={(event) => {
                          event.stopPropagation();
                          deleteRubric.mutate(rubric.id);
                        }}
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>

      <RubricFormDialog open={showCreate} onOpenChange={setShowCreate} />
      <RubricFormDialog
        open={!!editRubric}
        onOpenChange={(open) => {
          if (!open) setEditRubric(null);
        }}
        rubric={editRubric}
      />

      <Dialog
        open={!!selectedRubric}
        onOpenChange={(open) => {
          if (!open) setSelectedRubric(null);
        }}
      >
        <DialogContent className="sm:max-w-[95vw] max-h-[92vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>{selectedRubric?.name}</DialogTitle>
            <DialogDescription>
              {t("rubrics.detailDescription")}
            </DialogDescription>
          </DialogHeader>

          {selectedRubric ? (
            <div className="space-y-3">
              <p className="text-xs text-muted-foreground">
                {t("rubrics.levelMeaningHint")}
              </p>
              <RubricMatrixView
                content={normalizeContent(selectedRubric.content)}
              />
            </div>
          ) : null}
        </DialogContent>
      </Dialog>
    </div>
  );
}
