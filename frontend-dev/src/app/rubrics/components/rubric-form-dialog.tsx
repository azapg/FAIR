import { useEffect, useState } from "react";
import { Plus, Sparkles, Trash2, X } from "lucide-react";
import { useTranslation } from "react-i18next";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Textarea } from "@/components/ui/textarea";

import {
  Rubric,
  RubricContent,
  useCreateRubric,
  useGenerateRubric,
  useUpdateRubric,
} from "@/hooks/use-rubrics";

import { DEFAULT_CONTENT, normalizeContent } from "../utils";
import { EditableCriterion, INLINE_INPUT_CLASSNAME } from "../types";
import { InlineEditableDescription } from "./inline-editable-description";

export function RubricFormDialog({
  open,
  onOpenChange,
  rubric,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  rubric?: Rubric | null;
}) {
  const { t } = useTranslation();
  const isEdit = !!rubric;
  const [name, setName] = useState("");
  const [levels, setLevels] = useState<string[]>([]);
  const [criteria, setCriteria] = useState<EditableCriterion[]>([]);
  const [instruction, setInstruction] = useState("");
  const [formError, setFormError] = useState<string | null>(null);
  const createRubric = useCreateRubric();
  const updateRubric = useUpdateRubric();
  const generateRubric = useGenerateRubric();

  const pending =
    createRubric.isPending ||
    updateRubric.isPending ||
    generateRubric.isPending;

  useEffect(() => {
    if (!open) return;
    const source = normalizeContent(rubric?.content ?? DEFAULT_CONTENT);
    setName(rubric?.name ?? "");
    setLevels(source.levels);
    setCriteria(source.criteria);
    setInstruction("");
    setFormError(null);
  }, [open, rubric]);

  const updateCriterionLevel = (
    criterionIndex: number,
    levelIndex: number,
    value: string,
  ) => {
    setCriteria((previous) =>
      previous.map((criterion, index) =>
        index === criterionIndex
          ? {
              ...criterion,
              levels: criterion.levels.map((levelValue, cellIndex) =>
                cellIndex === levelIndex ? value : levelValue,
              ),
            }
          : criterion,
      ),
    );
  };

  const addLevel = () => {
    const nextLevel = `${t("rubrics.levelLabel")} ${levels.length + 1}`;
    setLevels((previous) => [...previous, nextLevel]);
    setCriteria((previous) =>
      previous.map((criterion) => ({
        ...criterion,
        levels: [...criterion.levels, ""],
      })),
    );
  };

  const removeLevel = (levelIndex: number) => {
    if (levels.length <= 1) return;
    setLevels((previous) =>
      previous.filter((_, index) => index !== levelIndex),
    );
    setCriteria((previous) =>
      previous.map((criterion) => ({
        ...criterion,
        levels: criterion.levels.filter((_, index) => index !== levelIndex),
      })),
    );
  };

  const addCriterion = () => {
    setCriteria((previous) => [
      ...previous,
      { name: "", weight: 0, levels: levels.map(() => "") },
    ]);
  };

  const removeCriterion = (criterionIndex: number) => {
    setCriteria((previous) =>
      previous.filter((_, index) => index !== criterionIndex),
    );
  };

  const handleGenerate = async () => {
    setFormError(null);
    if (!instruction.trim()) {
      setFormError(t("rubrics.messages.instructionRequired"));
      return;
    }
    try {
      const generated = await generateRubric.mutateAsync({
        instruction: instruction.trim(),
      });
      const normalized = normalizeContent(generated.content);
      setLevels(normalized.levels);
      setCriteria(normalized.criteria);
    } catch (err: any) {
      setFormError(
        err?.response?.data?.detail ?? err?.message ?? t("common.error"),
      );
    }
  };

  const handleSubmit = async () => {
    setFormError(null);
    if (!name.trim()) {
      setFormError(t("rubrics.messages.nameRequired"));
      return;
    }

    const payload: RubricContent = {
      levels: levels.map((level) => level.trim()),
      criteria: criteria.map((criterion) => ({
        name: criterion.name.trim(),
        weight: Number(criterion.weight),
        levels: criterion.levels.map((levelText) => levelText.trim()),
      })),
    };

    try {
      if (isEdit && rubric) {
        await updateRubric.mutateAsync({
          id: rubric.id,
          data: { name: name.trim(), content: payload },
        });
      } else {
        await createRubric.mutateAsync({ name: name.trim(), content: payload });
      }
      onOpenChange(false);
    } catch (err: any) {
      setFormError(
        err?.response?.data?.detail ?? err?.message ?? t("common.error"),
      );
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[70vw] h-[90vh]">
        <ScrollArea className="overflow-y-hidden max-h-screen">
          <DialogHeader className="pb-4">
            <DialogTitle>
              {isEdit ? t("rubrics.editTitle") : t("rubrics.createTitle")}
            </DialogTitle>
            <DialogDescription>
              {t("rubrics.formDescription")}
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div className="grid gap-2">
              <Label htmlFor="rubric-name">{t("rubrics.name")}</Label>
              <Input
                id="rubric-name"
                value={name}
                onChange={(event) => setName(event.target.value)}
                placeholder={t("rubrics.namePlaceholder")}
              />
            </div>

            <div className="rounded-xl border bg-gradient-to-tl from-amber-100 to-cyan-100 dark:from-amber-300 dark:to-cyan-400 p-4 space-y-3">
              <div className="flex items-center gap-2 text-sm font-medium">
                <Sparkles className="h-4 w-4" />
                {t("rubrics.aiTitle")}
              </div>
              <Textarea
                value={instruction}
                onChange={(event) => setInstruction(event.target.value)}
                placeholder={t("rubrics.aiPlaceholder")}
                className="min-h-24 text-foreground dark:placeholder:text-foreground/90"
              />
              <div className="flex flex-col items-end">
                <Button
                  variant="secondary"
                  onClick={handleGenerate}
                  disabled={pending}
                  className="w-min"
                >
                  {generateRubric.isPending
                    ? t("rubrics.generating")
                    : t("rubrics.generate")}
                </Button>
              </div>
            </div>

            <p className="text-xs text-muted-foreground">
              {t("rubrics.levelMeaningHint")}
            </p>
            <p className="text-xs text-muted-foreground">
              {t("rubrics.weightHint")}
            </p>

            <div className="rounded-lg border overflow-hidden">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-[18%]">
                      {t("rubrics.criterion")}
                    </TableHead>
                    <TableHead className="w-[10%]">
                      {t("rubrics.weight")}
                    </TableHead>
                    {levels.map((level, levelIndex) => (
                      <TableHead key={`level-header-${levelIndex}`}>
                        <div className="space-y-2">
                          <div className="flex items-center gap-2">
                            <Input
                              value={level}
                              onChange={(event) =>
                                setLevels((previous) =>
                                  previous.map((value, index) =>
                                    index === levelIndex
                                      ? event.target.value
                                      : value,
                                  ),
                                )
                              }
                              className={INLINE_INPUT_CLASSNAME}
                            />
                            <Button
                              size="icon"
                              variant="ghost"
                              onClick={() => removeLevel(levelIndex)}
                              disabled={levels.length <= 1}
                            >
                              <X className="h-4 w-4" />
                            </Button>
                          </div>
                        </div>
                      </TableHead>
                    ))}
                    <TableHead className="w-[4%]" />
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {criteria.map((criterion, criterionIndex) => (
                    <TableRow key={`criterion-${criterionIndex}`}>
                      <TableCell>
                        <Input
                          value={criterion.name}
                          onChange={(event) =>
                            setCriteria((previous) =>
                              previous.map((item, index) =>
                                index === criterionIndex
                                  ? { ...item, name: event.target.value }
                                  : item,
                              ),
                            )
                          }
                          placeholder={t("rubrics.criterionPlaceholder")}
                          className={INLINE_INPUT_CLASSNAME}
                        />
                      </TableCell>
                      <TableCell>
                        <Input
                          type="number"
                          step="any"
                          min={0}
                          max={1}
                          value={criterion.weight}
                          onChange={(event) =>
                            setCriteria((previous) =>
                              previous.map((item, index) =>
                                index === criterionIndex
                                  ? {
                                      ...item,
                                      weight: Number(event.target.value),
                                    }
                                  : item,
                              ),
                            )
                          }
                          className={`${INLINE_INPUT_CLASSNAME} text-right [appearance:textfield] [&::-webkit-outer-spin-button]:appearance-none [&::-webkit-inner-spin-button]:appearance-none [&::-webkit-outer-spin-button]:m-0 [&::-webkit-inner-spin-button]:m-0`}
                        />
                      </TableCell>
                      {levels.map((_, levelIndex) => (
                        <TableCell
                          key={`criterion-${criterionIndex}-level-${levelIndex}`}
                        >
                          <InlineEditableDescription
                            value={criterion.levels[levelIndex] ?? ""}
                            onChange={(nextValue) =>
                              updateCriterionLevel(
                                criterionIndex,
                                levelIndex,
                                nextValue,
                              )
                            }
                            placeholder={t("rubrics.levelCriteriaPlaceholder")}
                          />
                        </TableCell>
                      ))}
                      <TableCell>
                        <Button
                          size="icon"
                          variant="ghost"
                          onClick={() => removeCriterion(criterionIndex)}
                          disabled={criteria.length <= 1}
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>

            <div className="flex flex-wrap gap-2">
              <Button variant="outline" onClick={addCriterion}>
                <Plus className="h-4 w-4 mr-2" />
                {t("rubrics.addCriterion")}
              </Button>
              <Button variant="outline" onClick={addLevel}>
                <Plus className="h-4 w-4 mr-2" />
                {t("rubrics.addLevel")}
              </Button>
            </div>

            {formError ? (
              <p className="text-sm text-destructive bg-destructive/10 rounded-md p-2">
                {formError}
              </p>
            ) : null}
          </div>
        </ScrollArea>

        <DialogFooter>
          <Button
            variant="outline"
            onClick={() => onOpenChange(false)}
            disabled={pending}
          >
            {t("common.cancel")}
          </Button>
          <Button onClick={handleSubmit} disabled={pending}>
            {isEdit ? t("common.save") : t("common.create")}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
