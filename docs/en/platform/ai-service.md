---
title: AI Service
description: Configure the global LLM settings used by FAIR features.
---

FAIR uses a global AI service for features that create content with a language model, such as rubric generation. These features require an administrator to configure the model provider before users can run them.

## Required configuration

Set the API key in the environment where the FAIR backend runs:

```bash
FAIR_LLM_API_KEY="your-provider-api-key"
```

If this value is missing, FAIR will show users a friendly configuration message instead of exposing provider-specific connection details.

## Optional configuration

Use these environment variables when you need a custom provider endpoint or model:

| Variable | Default | Description |
|---|---|---|
| `FAIR_LLM_BASE_URL` | `https://api.openai.com/v1` | Base URL for the OpenAI-compatible chat completions API. |
| `FAIR_LLM_MODEL` | `gpt-4o` | Model name used for backend AI features. |

## After changing settings

Restart the FAIR backend after updating these values so the service reads the new environment. Then try a feature such as rubric generation from a professor account to confirm the configuration works.
