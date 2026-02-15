import { useEffect, useMemo, useState } from "react";
import { Pencil, Plus, Sparkles, Trash2, X } from "lucide-react";

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
  RubricCriterion,
  useCreateRubric,
  useDeleteRubric,
  useGenerateRubric,
  useRubrics,
  useUpdateRubric,
} from "@/hooks/use-rubrics";
import { useTranslation } from "react-i18next";
import { ScrollArea } from "@/components/ui/scroll-area";

const DEFAULT_CONTENT: RubricContent = {
  levels: ["Poor", "Fair", "Good", "Excellent"],
  criteria: [
    {
      name: "Content",
      weight: 0.5,
      levels: [
        "No work was submitted",
        "Shows minimal understanding",
        "Meets expectations",
        "Shows deep and clear mastery",
      ],
    },
    {
      name: "Organization",
      weight: 0.5,
      levels: [
        "No clear structure",
        "Basic structure with gaps",
        "Clear and coherent structure",
        "Excellent flow and cohesion",
      ],
    },
  ],
};

type EditableCriterion = {
  name: string;
  weight: number;
  levels: string[];
};

const INLINE_INPUT_CLASSNAME =
  "h-8 border-transparent bg-transparent shadow-none px-2 py-0 text-sm focus-visible:border-border focus-visible:ring-1 focus-visible:ring-ring/40 focus-visible:bg-muted/20";

function InlineEditableDescription({
  value,
  onChange,
  placeholder,
}: {
  value: string;
  onChange: (value: string) => void;
  placeholder: string;
}) {
  const [isEditing, setIsEditing] = useState(false);

  if (!isEditing) {
    return (
      <button
        type="button"
        className="w-full rounded-md p-2 text-left hover:bg-muted/40 transition-colors"
        onClick={() => setIsEditing(true)}
      >
        <p
          className={`text-sm whitespace-pre-wrap break-words line-clamp-3 ${
            value ? "text-foreground" : "text-muted-foreground italic"
          }`}
        >
          {value || placeholder}
        </p>
      </button>
    );
  }

  return (
    <Textarea
      autoFocus
      rows={4}
      value={value}
      onChange={(event) => onChange(event.target.value)}
      onBlur={() => setIsEditing(false)}
      onKeyDown={(event) => {
        if (event.key === "Escape") {
          setIsEditing(false);
        }
      }}
      className="min-h-24 text-sm border-border/50 focus-visible:ring-1 focus-visible:ring-ring/40"
      placeholder={placeholder}
    />
  );
}

function normalizeContent(content: RubricContent): RubricContent {
  const levels = content.levels.length > 0 ? content.levels : ["Level 1"];
  const criteria: RubricCriterion[] = content.criteria.map((criterion) => ({
    ...criterion,
    levels: levels.map((_, index) => criterion.levels[index] ?? ""),
  }));
  return { levels, criteria };
}

function RubricMatrixView({ content }: { content: RubricContent }) {
  return (
    <div className="rounded-lg border overflow-hidden">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead className="w-[24%]">Criterion</TableHead>
            <TableHead className="w-[10%]">Weight</TableHead>
            {content.levels.map((level, index) => (
              <TableHead key={`${level}-${index}`}>{level}</TableHead>
            ))}
          </TableRow>
        </TableHeader>
        <TableBody>
          {content.criteria.map((criterion) => (
            <TableRow key={criterion.name}>
              <TableCell className="font-medium">{criterion.name}</TableCell>
              <TableCell>{Math.round(criterion.weight * 100)}%</TableCell>
              {criterion.levels.map((description, index) => (
                <TableCell key={`${criterion.name}-${index}`}>
                  {description}
                </TableCell>
              ))}
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}

function RubricFormDialog({
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
