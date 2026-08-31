import { agentCapability } from '@fair/sdk';

/**
 * A chat agent with no model behind it.
 *
 * Two jobs: it demonstrates the `run` form of the SDK (yield strings, the SDK
 * handles chunking, message lifecycle and the terminal outcome), and it gives
 * the platform a streaming agent that works with no provider configured -- so
 * the chat pipeline can be exercised end to end on a laptop with nothing
 * installed.
 */
export const echo = agentCapability({
  id: 'echo',
  name: 'Echo (no model)',
  description: 'Streams a canned reply. Useful for testing the chat pipeline.',
  async *run(turn, ctx) {
    await ctx.log('echo received a turn', { characters: turn.text.length });

    const words = `You said: ${turn.text}. `.split(' ');
    for (const word of words) {
      if (ctx.signal.aborted) return;
      yield word + ' ';
      await sleep(40);
    }

    yield '\n\nThis reply was streamed from a FAIR extension over the ';
    yield 'Execution protocol: every chunk you just read is a durable event, ';
    yield 'so reloading this page replays it exactly.';
  },
});

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}
