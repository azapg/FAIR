import { flowStep } from '@fair/sdk';

/**
 * Flow steps for the demo Flow.
 *
 * Flow steps are deliberately plain functions: a reproducible benchmark wants
 * a deterministic input -> output contract, not a conversation. FAIR pins the
 * exact capability version onto a published FlowVersion, so re-running the
 * same Flow over the same inputs gives the same pipeline every time -- which
 * is what makes comparing two Flows a valid measurement.
 *
 * Nothing here calls a model, on purpose: the demo Flow should show the shape
 * and the pinning, not depend on a provider being up.
 */

export const extractText = flowStep<
  { flowInput?: { text?: string } },
  { text: string; characters: number }
>({
  id: 'extract.text',
  name: 'Extract text',
  outputSchema: {
    type: 'object',
    properties: {
      text: { type: 'string' },
      characters: { type: 'number' },
    },
    required: ['text', 'characters'],
  },
  async run(input, ctx) {
    const text = input.flowInput?.text ?? '';
    await ctx.log('extracted text', { characters: text.length });
    return { text, characters: text.length };
  },
});

export const scoreText = flowStep<
  { previousOutput?: { text?: string } },
  { score: number; wordCount: number; rationale: string }
>({
  id: 'score.text',
  name: 'Score text',
  outputSchema: {
    type: 'object',
    properties: {
      score: { type: 'number' },
      wordCount: { type: 'number' },
      rationale: { type: 'string' },
    },
    required: ['score', 'wordCount', 'rationale'],
  },
  async run(input, ctx) {
    const text = input.previousOutput?.text ?? '';
    const words = text.split(/\s+/).filter(Boolean);
    // A deterministic stand-in for a grader: length-based, capped at 100.
    const score = Math.min(100, words.length * 5);
    await ctx.log('scored text', { words: words.length, score });
    return {
      score,
      wordCount: words.length,
      rationale: `Scored ${score}/100 from ${words.length} words.`,
    };
  },
});

export const summarize = flowStep<
  { previousOutput?: { score?: number; rationale?: string } },
  { summary: string; score: number }
>({
  id: 'summarize.result',
  name: 'Summarize result',
  outputSchema: {
    type: 'object',
    properties: {
      summary: { type: 'string' },
      score: { type: 'number' },
    },
    required: ['summary', 'score'],
  },
  async run(input, ctx) {
    const score = input.previousOutput?.score ?? 0;
    const rationale = input.previousOutput?.rationale ?? 'no rationale';

    // A Flow step can leave a durable, provenance-stamped artifact behind.
    // This is what a research run would export and compare against.
    await ctx.artifacts.create({
      title: 'Demo flow result',
      kindUri: 'urn:fair:artifact:flow-demo-result',
      inlineJson: { score, rationale },
    });

    return { summary: `Final score ${score}/100. ${rationale}`, score };
  },
});
