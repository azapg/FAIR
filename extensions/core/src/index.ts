/**
 * FAIR core extension.
 *
 * These are FAIR's own built-in capabilities, written on the public SDK with
 * no privileged access. If something here needs a shortcut the SDK does not
 * offer, that is a bug in the SDK, not a reason for a private API.
 *
 *   bun run dev
 */
import { createExtension } from '@fair/sdk';
import { tutor } from './tutor.js';
import { echo } from './echo.js';
import { rubricGenerator } from './rubric.js';
import { extractText, scoreText, summarize } from './flow-steps.js';

const extension = createExtension({
  id: 'fair.core',
  name: 'FAIR Core',
  version: '0.1.0',
  capabilities: [
    // chat.agent -- appear in the model selector
    tutor,
    echo,
    // function -- render as a button wherever the contract is placed
    rubricGenerator,
    // flow.step -- selectable as pinned Flow nodes
    extractText,
    scoreText,
    summarize,
  ],
});

await extension.start();
