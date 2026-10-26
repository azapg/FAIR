import { agentCapability } from '@fair/sdk';
import { createOpenAICompatible } from '@ai-sdk/openai-compatible';
import { ToolLoopAgent } from 'ai';

/**
 * A chat agent backed by a local Ollama model.
 *
 * This is the DX the SDK exists for: build the agent however you like with the
 * AI SDK, then hand the object to FAIR. We never modify it -- we call its own
 * stream() and mirror the parts it already emits into the Execution log. Tool
 * calls, reasoning and errors are recorded without you wiring anything up.
 */
const ollama = createOpenAICompatible({
  name: 'ollama',
  baseURL: process.env.OLLAMA_URL ?? 'http://127.0.0.1:11434/v1',
});

const agent = new ToolLoopAgent({
  model: ollama(process.env.OLLAMA_MODEL ?? 'gemma3:270m'),
  instructions:
    'You are a teaching assistant. Be brief. Guide the student towards the ' +
    'answer with questions rather than stating it outright.',
});

export const tutor = agentCapability({
  id: 'tutor',
  name: 'Socratic Tutor (gemma3)',
  description: 'A local gemma3:270m tutor that never gives the answer away.',
  agent,
});
