import { RubricContent, RubricCriterion } from "@/hooks/use-rubrics";

export const DEFAULT_CONTENT: RubricContent = {
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

export function normalizeContent(content: RubricContent): RubricContent {
  const levels = content.levels.length > 0 ? content.levels : ["Level 1"];
  const criteria: RubricCriterion[] = content.criteria.map((criterion) => ({
    ...criterion,
    levels: levels.map((_, index) => criterion.levels[index] ?? ""),
  }));
  return { levels, criteria };
}
