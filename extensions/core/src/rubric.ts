import { functionCapability } from '@fair/sdk';

interface RubricInput {
  title?: string;
  topic?: string;
  maxPoints?: number;
  criteriaCount?: number;
}

interface RubricCriterion {
  name: string;
  description: string;
  points: number;
}

interface RubricOutput {
  title: string;
  totalPoints: number;
  criteria: RubricCriterion[];
}

/**
 * An instance of the `fair.rubric.generate@1` contract.
 *
 * The contract -- not this extension -- owns the input/output schema and the
 * places a button for it appears (the Rubrics tab, the "no rubrics yet" empty
 * state on assignment creation). Implementing it is all it takes to light
 * those up. Adding a different kind of function later is a new contract, not a
 * protocol change.
 */
export const rubricGenerator = functionCapability<RubricInput, RubricOutput>({
  contract: 'fair.rubric.generate@1',
  name: 'Generate a rubric',
  async run(input, ctx) {
    const topic = input.topic ?? input.title ?? 'the assignment';
    const total = input.maxPoints ?? 100;
    const count = Math.min(Math.max(input.criteriaCount ?? 4, 1), 10);

    await ctx.log('generating rubric', { topic, total, count });

    // A deterministic split so the demo is reproducible. A real implementation
    // would call a model here -- the surrounding contract does not change.
    const names = [
      'Understanding',
      'Reasoning',
      'Evidence',
      'Communication',
      'Structure',
      'Originality',
      'Accuracy',
      'Completeness',
      'Method',
      'Reflection',
    ].slice(0, count);

    const base = Math.floor(total / count);
    const criteria = names.map((name, index) => ({
      name,
      description: `Demonstrates ${name.toLowerCase()} of ${topic}.`,
      // Give the remainder to the first criterion so the total is exact.
      points: index === 0 ? total - base * (count - 1) : base,
    }));

    return { title: `Rubric for ${topic}`, totalPoints: total, criteria };
  },
});
