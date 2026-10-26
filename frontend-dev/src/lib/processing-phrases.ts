const NORMAL_PHRASES = [
  "Calculating", "Computing", "Processing", "Analyzing", "Generating", "Initializing", 
  "Synthesizing", "Compiling", "Parsing", "Evaluating", "Interpreting", "Scoring", 
  "Validating", "Cross-checking", "Aggregating", "Drafting", "Composing", "Reasoning", 
  "Loading context", "Assembling response"
];

const LEARNING_PHRASES = [
  "Grading", "Studying", "Annotating", "Proofreading", "Fact-checking", "Rubric-matching", 
  "Cross-referencing", "Benchmarking", "Highlighting", "Weighing the evidence", 
  "Partial-crediting", "Curving the results", "Double-checking citations", 
  "Reading between the lines", "Chasing down sources", "Tallying the score", 
  "Consulting the syllabus", "Sharpening the red pen", "Flipping through notes", 
  "Office-houring", "Footnoting"
];

const EASTER_EGGS = [
  "Interpreting the interpreter", "Grading the grader", "Artifacting the artifact", 
  "Convening the agent committee", "Paging the subagent", "Waking the pipeline", 
  "Consulting Nightingale", "Poking the interpreter", "Nudging the grader", 
  "Reticulating rubrics"
];

function sample(arr: string[]): string {
  return arr[Math.floor(Math.random() * arr.length)];
}

/**
 * Returns a random processing phrase based on how many seconds have elapsed.
 * - Early on (elapsed < 5s), it always returns a normal phrase.
 * - As time goes on, the chance of learning phrases and easter eggs increases.
 */
export function getRandomProcessingPhrase(elapsedSeconds: number): string {
  const rand = Math.random();

  if (elapsedSeconds < 3) {
    return sample(NORMAL_PHRASES);
  } else if (elapsedSeconds < 8) {
    if (rand < 0.2) return sample(LEARNING_PHRASES);
    return sample(NORMAL_PHRASES);
  } else if (elapsedSeconds < 15) {
    if (rand < 0.05) return sample(EASTER_EGGS);
    if (rand < 0.40) return sample(LEARNING_PHRASES);
    return sample(NORMAL_PHRASES);
  } else {
    if (rand < 0.10) return sample(EASTER_EGGS);
    if (rand < 0.60) return sample(LEARNING_PHRASES);
    return sample(NORMAL_PHRASES);
  }
}
