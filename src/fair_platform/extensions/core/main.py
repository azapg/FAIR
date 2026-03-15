import asyncio
import base64
import json
import os
import re
import tempfile
from pathlib import Path
from typing import Any, Optional, Tuple

from dotenv import load_dotenv
from openai import AsyncOpenAI, OpenAI

from fair_platform.extension_sdk import (
    NumberField,
    FairExtension,
    JobContext,
    PluginDescriptor,
    SecretField,
    SettingsSchema,
    SwitchField,
    TextField,
    WorkflowStepExecutionRequest,
)
from fair_platform.extension_sdk.client import build_platform_client
from fair_platform.extension_sdk.contracts.rubric import RubricJobRequest

load_dotenv()

FAIR_CORE_LLM_API_KEY: Optional[str] = (
    os.getenv("FAIR_CORE_LLM_API_KEY") or os.getenv("FAIR_LLM_API_KEY")
)
FAIR_CORE_LLM_BASE_URL: str = (
    os.getenv("FAIR_CORE_LLM_BASE_URL")
    or os.getenv("FAIR_LLM_BASE_URL")
    or "https://api.openai.com/v1"
)
FAIR_CORE_LLM_MODEL: str = (
    os.getenv("FAIR_CORE_LLM_MODEL")
    or os.getenv("FAIR_LLM_MODEL")
    or "gpt-5.4-2026-03-05"
)


def _env_float(name: str, default: float) -> float:
    raw = os.getenv(name, "").strip()
    if not raw:
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def _env_int(name: str, default: Optional[int]) -> Optional[int]:
    raw = os.getenv(name, "").strip()
    if not raw:
        return default
    try:
        value = int(raw)
        return value if value > 0 else default
    except ValueError:
        return default


FAIR_CORE_LLM_TEMPERATURE: float = _env_float(
    "FAIR_CORE_LLM_TEMPERATURE", _env_float("FAIR_LLM_TEMPERATURE", 1.0)
)
FAIR_CORE_LLM_MAX_TOKENS: Optional[int] = _env_int(
    "FAIR_CORE_LLM_MAX_TOKENS", _env_int("FAIR_LLM_MAX_TOKENS", None)
)

_ai_client: Optional[AsyncOpenAI] = None


def _get_ai_client(
    *,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
) -> AsyncOpenAI:
    global _ai_client
    resolved_key = api_key or FAIR_CORE_LLM_API_KEY
    resolved_base_url = base_url or FAIR_CORE_LLM_BASE_URL
    if api_key or base_url:
        if not resolved_key:
            raise RuntimeError(
                "Missing FAIR_CORE_LLM_API_KEY (or FAIR_LLM_API_KEY) for core extension LLM calls."
            )
        return AsyncOpenAI(
            api_key=resolved_key,
            base_url=resolved_base_url,
        )
    if _ai_client is None:
        if not resolved_key:
            raise RuntimeError(
                "Missing FAIR_CORE_LLM_API_KEY (or FAIR_LLM_API_KEY) for core extension LLM calls."
            )
        _ai_client = AsyncOpenAI(
            api_key=resolved_key,
            base_url=resolved_base_url,
        )
    return _ai_client


def _extract_json_object(content: str) -> dict[str, Any]:
    cleaned = content.strip()
    code_block_match = re.search(r"```(?:json)?\s*(\{[\s\S]*\})\s*```", cleaned)
    if code_block_match:
        cleaned = code_block_match.group(1).strip()
    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError:
        first_brace = cleaned.find("{")
        last_brace = cleaned.rfind("}")
        if first_brace == -1 or last_brace == -1 or first_brace >= last_brace:
            raise ValueError("LLM output did not contain a JSON object.")
        parsed = json.loads(cleaned[first_brace:last_brace + 1])
    if not isinstance(parsed, dict):
        raise ValueError("LLM output JSON must be an object.")
    return parsed


async def _call_llm(
    messages: list[dict[str, str]],
    *,
    model: Optional[str] = None,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
    base_url: Optional[str] = None,
    api_key: Optional[str] = None,
) -> str:
    client = _get_ai_client(api_key=api_key, base_url=base_url)
    params: dict[str, Any] = {
        "model": model or FAIR_CORE_LLM_MODEL,
        "messages": messages,
        "temperature": FAIR_CORE_LLM_TEMPERATURE if temperature is None else temperature,
    }
    resolved_max_tokens = max_tokens if max_tokens is not None else FAIR_CORE_LLM_MAX_TOKENS
    if resolved_max_tokens:
        params["max_tokens"] = resolved_max_tokens
    response = await client.chat.completions.create(**params)
    content = response.choices[0].message.content if response.choices else None
    if not content:
        raise RuntimeError("LLM returned empty response.")
    return content.strip()


def _format_submission_context(submission: Any) -> str:
    artifacts = []
    for artifact in submission.artifacts or []:
        artifacts.append(
            {
                "artifact_id": artifact.artifact_id,
                "title": artifact.title,
                "mime": artifact.mime,
                "kind": artifact.kind,
            }
        )
    payload = {
        "submission_id": submission.submission_id,
        "assignment_id": submission.assignment_id,
        "status": submission.status,
        "metadata": submission.metadata,
        "artifacts": artifacts,
        "state": {
            "transcription": submission.state.transcription,
            "grade": submission.state.grade,
            "feedback": submission.state.feedback,
            "review_comments": submission.state.review_comments,
            "review_flags": submission.state.review_flags,
        },
    }
    return json.dumps(payload, ensure_ascii=True, indent=2)


def _filename_from_disposition(disposition: str | None) -> Optional[str]:
    if not disposition:
        return None
    match = re.search(r'filename="([^"]+)"', disposition)
    if match:
        return match.group(1)
    match = re.search(r"filename=([^;]+)", disposition)
    if match:
        return match.group(1).strip().strip('"')
    return None


async def _download_artifact_bytes(
    artifact_id: str,
    *,
    platform_url: str,
    credentials: Any,
) -> Tuple[bytes, str, str]:
    async with build_platform_client(platform_url=platform_url, credentials=credentials) as http:
        response = await http.get(f"/api/artifacts/extensions/{artifact_id}/download")
        response.raise_for_status()
        content_type = response.headers.get("content-type") or "application/octet-stream"
        filename = _filename_from_disposition(response.headers.get("content-disposition"))
        if not filename:
            filename = f"{artifact_id}"
        return response.content, filename, content_type


def _bytes_to_base64(data: bytes, mime: str, include_prefix: bool = True) -> str:
    encoded = base64.b64encode(data).decode("utf-8")
    if include_prefix:
        return f"data:{mime};base64,{encoded}"
    return encoded


def _resolve_llm_settings(settings: dict[str, Any]) -> dict[str, Any]:
    temperature = FAIR_CORE_LLM_TEMPERATURE
    if settings.get("temperature") is not None:
        try:
            temperature = float(settings.get("temperature"))
        except (TypeError, ValueError):
            temperature = FAIR_CORE_LLM_TEMPERATURE

    max_tokens = FAIR_CORE_LLM_MAX_TOKENS
    if settings.get("maxTokens") is not None:
        try:
            max_value = int(settings.get("maxTokens"))
            max_tokens = max_value if max_value > 0 else FAIR_CORE_LLM_MAX_TOKENS
        except (TypeError, ValueError):
            max_tokens = FAIR_CORE_LLM_MAX_TOKENS

    return {
        "model": str(settings.get("model") or FAIR_CORE_LLM_MODEL).strip() or FAIR_CORE_LLM_MODEL,
        "base_url": str(settings.get("baseUrl") or FAIR_CORE_LLM_BASE_URL).strip() or FAIR_CORE_LLM_BASE_URL,
        "api_key": str(settings.get("apiKey") or FAIR_CORE_LLM_API_KEY or "").strip() or None,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }


def _bool_setting(value: Any, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return bool(value)


def _resolve_openai_transcription_settings(settings: dict[str, Any]) -> dict[str, Any]:
    temperature = FAIR_CORE_LLM_TEMPERATURE
    if settings.get("openaiTemperature") is not None:
        try:
            temperature = float(settings.get("openaiTemperature"))
        except (TypeError, ValueError):
            temperature = FAIR_CORE_LLM_TEMPERATURE

    max_tokens = FAIR_CORE_LLM_MAX_TOKENS
    if settings.get("openaiMaxTokens") is not None:
        try:
            max_value = int(settings.get("openaiMaxTokens"))
            max_tokens = max_value if max_value > 0 else FAIR_CORE_LLM_MAX_TOKENS
        except (TypeError, ValueError):
            max_tokens = FAIR_CORE_LLM_MAX_TOKENS

    return {
        "model": str(settings.get("openaiModel") or FAIR_CORE_LLM_MODEL).strip() or FAIR_CORE_LLM_MODEL,
        "base_url": str(settings.get("openaiBaseUrl") or FAIR_CORE_LLM_BASE_URL).strip() or FAIR_CORE_LLM_BASE_URL,
        "api_key": str(settings.get("openaiApiKey") or FAIR_CORE_LLM_API_KEY or "").strip() or None,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "prompt": str(settings.get("openaiPrompt") or "Extract a clear markdown transcription of the provided file.").strip(),
    }


def _resolve_zai_settings(settings: dict[str, Any]) -> dict[str, Any]:
    return {
        "api_key": str(settings.get("zaiApiKey") or os.getenv("FAIR_CORE_ZAI_API_KEY", "")).strip() or None,
        "model": str(settings.get("zaiModel") or "GLM-OCR").strip() or "GLM-OCR",
        "show_visualization": bool(settings.get("zaiShowVisualization", False)),
    }


def _openai_file_transcription(
    *,
    client: OpenAI,
    file_path: Path,
    prompt: str,
    model: str,
    temperature: float,
    max_tokens: Optional[int],
) -> str:
    with open(file_path, "rb") as handle:
        uploaded = client.files.create(
            file=handle,
            purpose="user_data",
        )
    input_payload = [
        {
            "role": "user",
            "content": [
                {"type": "input_file", "file_id": uploaded.id},
                {"type": "input_text", "text": prompt},
            ],
        }
    ]
    params: dict[str, Any] = {
        "model": model,
        "input": input_payload,
        "temperature": temperature,
    }
    if max_tokens:
        params["max_output_tokens"] = max_tokens
    response = client.responses.create(**params)
    output_text = getattr(response, "output_text", None)
    if not output_text:
        raise RuntimeError("OpenAI responses returned empty output.")
    return output_text


def _zai_file_transcription(
    *,
    api_key: str,
    file_b64: str,
    model: str,
    show_visualization: bool,
) -> str:
    try:
        from zai import ZaiClient
    except ImportError as exc:
        raise RuntimeError("Z.ai client not installed. Add the 'zai' package to use this mode.") from exc
    client = ZaiClient(api_key=api_key)
    response = client.layout_parsing.create(
        model=model,
        file=file_b64,
        return_crop_images=show_visualization,
        need_layout_visualization=show_visualization,
    )
    return response.md_results or ""


def _core_webhook_url() -> str:
    explicit = os.getenv("FAIR_CORE_EXTENSION_WEBHOOK_URL", "").strip()
    if explicit:
        return explicit
    host = os.getenv("FAIR_CORE_EXTENSION_HOST", "127.0.0.1").strip() or "127.0.0.1"
    port = os.getenv("FAIR_CORE_EXTENSION_PORT", "8001").strip() or "8001"
    return f"http://{host}:{port}/hooks/jobs"


core_extension = FairExtension(
    extension_id=os.getenv("FAIR_CORE_EXTENSION_ID", "fair.core"),
    platform_url=os.getenv("FAIR_CORE_PLATFORM_URL", "http://127.0.0.1:8000"),
    extension_secret=os.getenv("FAIR_CORE_EXTENSION_SECRET", "fair-core-dev-secret"),
    webhook_url=_core_webhook_url(),
    auto_connect=True,
    requested_scopes=["extensions:connect", "jobs:write", "jobs:read"],
    intents=["rubric.create"],
    capabilities=["rubrics"],
    metadata={"builtin": True, "name": "FAIR Core"},
    plugins=[
        PluginDescriptor(
            plugin_id="fair.core.transcriber.simple",
            extension_id=os.getenv("FAIR_CORE_EXTENSION_ID", "fair.core"),
            plugin_type="transcriber",
            name="Simple Transcriber",
            description="Transcribes submissions using OpenAI or Z.ai, depending on settings.",
            version="1.0.0",
            action="plugin.transcribe.simple",
            settings_schema=(
                SettingsSchema()
                .add(
                    "useOpenAI",
                    SwitchField(
                        fieldType="switch",
                        label="Use OpenAI",
                        description="Use OpenAI responses API for file transcription.",
                        required=False,
                        default=True,
                    ),
                )
                .add(
                    "openaiModel",
                    TextField(
                        fieldType="text",
                        label="OpenAI Model",
                        description="OpenAI model to use for file transcription.",
                        required=False,
                        default="gpt-5.4-2026-03-05",
                        minLength=1,
                        maxLength=100,
                    ),
                )
                .add(
                    "openaiBaseUrl",
                    TextField(
                        fieldType="text",
                        label="OpenAI Base URL",
                        description="OpenAI API base URL override.",
                        required=False,
                        default="https://api.openai.com/v1",
                        minLength=1,
                        maxLength=300,
                    ),
                )
                .add(
                    "openaiApiKey",
                    SecretField(
                        fieldType="secret",
                        label="OpenAI API Key",
                        description="Override OpenAI API key (optional, otherwise env).",
                        required=False,
                        default="",
                        minLength=0,
                        maxLength=400,
                    ),
                )
                .add(
                    "openaiTemperature",
                    NumberField(
                        fieldType="number",
                        label="OpenAI Temperature",
                        description="Sampling temperature for OpenAI responses.",
                        required=False,
                        default=0.7,
                        minimum=0,
                        maximum=2,
                        step=0.1,
                    ),
                )
                .add(
                    "openaiMaxTokens",
                    NumberField(
                        fieldType="number",
                        label="OpenAI Max Tokens",
                        description="Maximum output tokens for OpenAI responses.",
                        required=False,
                        default=800,
                        minimum=1,
                        maximum=8000,
                        step=1,
                    ),
                )
                .add(
                    "openaiPrompt",
                    TextField(
                        fieldType="text",
                        label="OpenAI Prompt",
                        description="Prompt to apply to uploaded files.",
                        required=False,
                        default="Extract a clear markdown transcription of the provided file.",
                        minLength=1,
                        maxLength=500,
                    ),
                )
                .add(
                    "zaiApiKey",
                    SecretField(
                        fieldType="secret",
                        label="Z.ai API Key",
                        description="Z.ai API key (required if OpenAI is disabled).",
                        required=False,
                        default="",
                        minLength=0,
                        maxLength=400,
                    ),
                )
                .add(
                    "zaiModel",
                    TextField(
                        fieldType="text",
                        label="Z.ai Model",
                        description="Z.ai model for OCR layout parsing.",
                        required=False,
                        default="GLM-OCR",
                        minLength=1,
                        maxLength=100,
                    ),
                )
                .add(
                    "zaiShowVisualization",
                    SwitchField(
                        fieldType="switch",
                        label="Show Z.ai Visualization",
                        description="Whether to request layout visualization from Z.ai.",
                        required=False,
                        default=False,
                    ),
                )
            ),
        ),
        PluginDescriptor(
            plugin_id="fair.core.grader.simple",
            extension_id=os.getenv("FAIR_CORE_EXTENSION_ID", "fair.core"),
            plugin_type="grader",
            name="Simple Grader",
            description="Assigns a basic score and feedback using the available transcription.",
            version="1.0.0",
            action="plugin.grade.simple",
            settings_schema=(
                SettingsSchema()
                .add(
                    "score",
                    NumberField(
                        fieldType="number",
                        label="Score",
                        description="Default score to assign.",
                        required=False,
                        default=85,
                        minimum=0,
                        maximum=100,
                        step=1,
                    ),
                )
                .add(
                    "model",
                    TextField(
                        fieldType="text",
                        label="LLM Model",
                        description="Override model for grading.",
                        required=False,
                        default="gpt-5.4-2026-03-05",
                        minLength=1,
                        maxLength=100,
                    ),
                )
                .add(
                    "baseUrl",
                    TextField(
                        fieldType="text",
                        label="LLM Base URL",
                        description="Override API base URL.",
                        required=False,
                        default="https://api.openai.com/v1",
                        minLength=1,
                        maxLength=300,
                    ),
                )
                .add(
                    "apiKey",
                    SecretField(
                        fieldType="secret",
                        label="LLM API Key",
                        description="Override API key (optional, otherwise env).",
                        required=False,
                        default="",
                        minLength=0,
                        maxLength=400,
                    ),
                )
                .add(
                    "temperature",
                    NumberField(
                        fieldType="number",
                        label="Temperature",
                        description="Sampling temperature.",
                        required=False,
                        default=0.7,
                        minimum=0,
                        maximum=2,
                        step=0.1,
                    ),
                )
                .add(
                    "maxTokens",
                    NumberField(
                        fieldType="number",
                        label="Max Tokens",
                        description="Maximum output tokens.",
                        required=False,
                        default=600,
                        minimum=1,
                        maximum=8000,
                        step=1,
                    ),
                )
            ),
        ),
        PluginDescriptor(
            plugin_id="fair.core.reviewer.simple",
            extension_id=os.getenv("FAIR_CORE_EXTENSION_ID", "fair.core"),
            plugin_type="reviewer",
            name="Simple Reviewer",
            description="Adds a lightweight review comment for each submission.",
            version="1.0.0",
            action="plugin.review.simple",
            settings_schema=(
                SettingsSchema()
                .add(
                    "reviewTone",
                    TextField(
                        fieldType="text",
                        label="Review Tone",
                        description="Tone to use in generated comments.",
                        required=False,
                        default="concise",
                        minLength=1,
                        maxLength=100,
                    ),
                )
                .add(
                    "model",
                    TextField(
                        fieldType="text",
                        label="LLM Model",
                        description="Override model for reviewing.",
                        required=False,
                        default="gpt-5.4-2026-03-05",
                        minLength=1,
                        maxLength=100,
                    ),
                )
                .add(
                    "baseUrl",
                    TextField(
                        fieldType="text",
                        label="LLM Base URL",
                        description="Override API base URL.",
                        required=False,
                        default="https://api.openai.com/v1",
                        minLength=1,
                        maxLength=300,
                    ),
                )
                .add(
                    "apiKey",
                    SecretField(
                        fieldType="secret",
                        label="LLM API Key",
                        description="Override API key (optional, otherwise env).",
                        required=False,
                        default="",
                        minLength=0,
                        maxLength=400,
                    ),
                )
                .add(
                    "temperature",
                    NumberField(
                        fieldType="number",
                        label="Temperature",
                        description="Sampling temperature.",
                        required=False,
                        default=0.7,
                        minimum=0,
                        maximum=2,
                        step=0.1,
                    ),
                )
                .add(
                    "maxTokens",
                    NumberField(
                        fieldType="number",
                        label="Max Tokens",
                        description="Maximum output tokens.",
                        required=False,
                        default=400,
                        minimum=1,
                        maximum=8000,
                        step=1,
                    ),
                )
            ),
        )
    ],
)


@core_extension.action("rubric.create")
async def create_rubric(ctx: JobContext, params: RubricJobRequest) -> dict:
    # NOTE: The frontend rubric stream currently times out after ~180s if no SSE events arrive.
    # Long LLM calls can exceed that and trigger "BodyStreamBuffer was aborted".
    # We should add periodic progress/heartbeat updates here later to keep the stream alive.
    await ctx.progress(10, "Reading rubric instruction", status="running")
    await ctx.log("info", "Generating rubric draft with LLM")
    system_prompt = (
        "You generate grading rubrics in strict JSON. "
        "Return only a JSON object, no markdown and no extra text."
    )
    user_prompt = (
        "Return a JSON object with this exact structure:\n"
        "{\n"
        '  "levels": ["Level 1", "Level 2", ...],\n'
        '  "criteria": [\n'
        "    {\n"
        '      "name": "Criterion name",\n'
        '      "weight": 0.25,\n'
        '      "levels": ["desc for level 1", "desc for level 2", ...]\n'
        "    }\n"
        "  ]\n"
        "}\n"
        "Rules:\n"
        "- criteria weights must sum exactly to 1.0\n"
        "- each criterion levels array length must match top-level levels length\n"
        "- keep names concise and clear\n"
        "- output valid JSON only\n"
        f"Instruction:\n{params.instruction}"
    )
    try:
        content_text = await _call_llm(
            [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ]
        )
        await ctx.progress(80, "Finalizing rubric")
        content = _extract_json_object(content_text)
    except Exception as exc:
        await ctx.log("error", f"Rubric LLM failed, using fallback: {str(exc)}")
        content = {
            "levels": ["Needs Improvement", "Developing", "Proficient", "Exemplary"],
            "criteria": [
                {
                    "name": "Instruction Alignment",
                    "weight": 0.4,
                    "levels": [
                        f"Limited alignment with: {params.instruction}",
                        f"Partial alignment with: {params.instruction}",
                        f"Strong alignment with: {params.instruction}",
                        f"Excellent alignment with: {params.instruction}",
                    ],
                },
                {
                    "name": "Evidence and Reasoning",
                    "weight": 0.35,
                    "levels": [
                        "Claims lack support",
                        "Some support with gaps",
                        "Clear support and reasoning",
                        "Compelling evidence with strong reasoning",
                    ],
                },
                {
                    "name": "Organization and Clarity",
                    "weight": 0.25,
                    "levels": [
                        "Disorganized and unclear",
                        "Partially organized",
                        "Well organized and clear",
                        "Highly coherent and polished",
                    ],
                },
            ],
        }
    return {
        "content": content,
    }


@core_extension.action("plugin.transcribe.simple")
async def simple_transcriber(ctx: JobContext, params: WorkflowStepExecutionRequest) -> dict:
    await ctx.progress(10, "Preparing transcription step", status="running")
    use_openai = _bool_setting(params.settings.get("useOpenAI", True), default=True)
    await ctx.log("info", f"Running simple transcriber using {'OpenAI' if use_openai else 'Z.ai'}")
    openai_settings = _resolve_openai_transcription_settings(params.settings)
    zai_settings = _resolve_zai_settings(params.settings)

    async def _transcribe_submission(submission):
        transcriptions: list[dict[str, Any]] = []
        for artifact in submission.artifacts or []:
            try:
                data, filename, mime = await _download_artifact_bytes(
                    artifact.artifact_id,
                    platform_url=core_extension.platform_url,
                    credentials=core_extension.credentials,
                )
            except Exception as exc:
                await ctx.log(
                    "warning",
                    f"Failed to download artifact {artifact.artifact_id}: {str(exc)}",
                )
                continue

            if use_openai:
                if openai_settings["api_key"]:
                    client = OpenAI(
                        api_key=openai_settings["api_key"],
                        base_url=openai_settings["base_url"],
                    )
                else:
                    client = OpenAI(base_url=openai_settings["base_url"])
                suffix = Path(filename).suffix or ".bin"
                fd, tmp_name = tempfile.mkstemp(suffix=suffix)
                os.close(fd)
                tmp_path = Path(tmp_name)
                try:
                    tmp_path.write_bytes(data)
                    prompt = f"{openai_settings['prompt']}\n\nArtifact title: {artifact.title or filename}"
                    transcription = await asyncio.to_thread(
                        _openai_file_transcription,
                        client=client,
                        file_path=tmp_path,
                        prompt=prompt,
                        model=openai_settings["model"],
                        temperature=openai_settings["temperature"],
                        max_tokens=openai_settings["max_tokens"],
                    )
                finally:
                    try:
                        tmp_path.unlink(missing_ok=True)
                    except Exception:
                        pass
            else:
                if not zai_settings["api_key"]:
                    raise RuntimeError("Missing Z.ai API key. Set FAIR_CORE_ZAI_API_KEY or zaiApiKey.")
                file_b64 = _bytes_to_base64(data, mime, include_prefix=True)
                transcription = await asyncio.to_thread(
                    _zai_file_transcription,
                    api_key=zai_settings["api_key"],
                    file_b64=file_b64,
                    model=zai_settings["model"],
                    show_visualization=zai_settings["show_visualization"],
                )

            transcriptions.append(
                {
                    "title": artifact.title or filename,
                    "content": transcription,
                    "artifact_id": artifact.artifact_id,
                }
            )

        if not transcriptions:
            context = _format_submission_context(submission)
            prompt = (
                "Create a clean markdown transcription based on the submission context. "
                "If the context lacks actual content, infer a concise summary from metadata "
                "without saying 'placeholder'.\n\n"
                f"Context:\n{context}"
            )
            transcription = await _call_llm(
                [
                    {"role": "system", "content": "You are a transcription assistant."},
                    {"role": "user", "content": prompt},
                ]
            )
        elif len(transcriptions) == 1:
            transcription = transcriptions[0]["content"]
        else:
            transcription = (
                f"The submission contains {len(transcriptions)} artifacts.\n\n"
                + "\n\n---\n\n".join(
                    f"## {item['title']}\n\n{item['content']}" for item in transcriptions
                )
            )

        item = {
            "transcription": transcription,
            "metadata": {
                "extension": "fair.core",
                "provider": "openai" if use_openai else "zai",
                "model": openai_settings["model"] if use_openai else zai_settings["model"],
            },
        }
        await ctx.submission_result(submission.submission_id, item)
        return {"submission_id": submission.submission_id, **item}

    results = await asyncio.gather(*(_transcribe_submission(submission) for submission in params.submissions))
    await ctx.progress(90, "Finalizing transcription")
    return {
        "plugin_type": "transcriber",
        "results": results,
        "metadata": {"completed_by": "fair.core.transcriber.simple"},
    }


@core_extension.action("plugin.grade.simple")
async def simple_grader(ctx: JobContext, params: WorkflowStepExecutionRequest) -> dict:
    await ctx.progress(10, "Preparing grading step", status="running")
    score = float(params.settings.get("score", 85))
    llm_settings = _resolve_llm_settings(params.settings)
    await ctx.log("info", f"Running simple grader with score={score}")

    async def _grade_submission(submission):
        transcription = submission.state.transcription or "No transcription provided."
        context = _format_submission_context(submission)
        prompt = (
            "Grade the submission on a 0-100 scale using the transcription and context. "
            "Return JSON only with keys: grade (number) and feedback (string).\n\n"
            f"Default score (only if truly necessary): {score}\n\n"
            f"Transcription:\n{transcription}\n\nContext:\n{context}"
        )
        content_text = await _call_llm(
            [
                {"role": "system", "content": "You are a fair, consistent grader."},
                {"role": "user", "content": prompt},
            ],
            model=llm_settings["model"],
            temperature=llm_settings["temperature"],
            max_tokens=llm_settings["max_tokens"],
            base_url=llm_settings["base_url"],
            api_key=llm_settings["api_key"],
        )
        try:
            payload = _extract_json_object(content_text)
            grade = float(payload.get("grade", score))
            grade = max(0.0, min(100.0, grade))
            feedback = str(payload.get("feedback") or content_text)
        except Exception:
            grade = score
            feedback = content_text
        item = {
            "grade": grade,
            "feedback": feedback,
            "metadata": {
                "score": score,
                "extension": "fair.core",
                "model": llm_settings["model"],
            },
        }
        await ctx.submission_result(submission.submission_id, item)
        return {"submission_id": submission.submission_id, **item}

    results = await asyncio.gather(*(_grade_submission(submission) for submission in params.submissions))
    await ctx.progress(90, "Finalizing grading")
    return {
        "plugin_type": "grader",
        "results": results,
        "metadata": {"completed_by": "fair.core.grader.simple"},
    }
    
@core_extension.action("plugin.review.simple")
async def simple_reviewer(ctx: JobContext, params: WorkflowStepExecutionRequest) -> dict:
    await ctx.progress(10, "Preparing review step", status="running")
    tone = str(params.settings.get("reviewTone", "concise")).strip() or "concise"
    llm_settings = _resolve_llm_settings(params.settings)
    await ctx.log("info", f"Running simple reviewer with tone={tone}")

    async def _review_submission(submission):
        context = _format_submission_context(submission)
        prompt = (
            "Provide reviewer comments and flags based on the submission context. "
            "Return JSON only with keys: comments (array of strings) and flags (array of strings). "
            f"Use a {tone} tone.\n\nContext:\n{context}"
        )
        content_text = await _call_llm(
            [
                {"role": "system", "content": "You are a helpful reviewer."},
                {"role": "user", "content": prompt},
            ],
            model=llm_settings["model"],
            temperature=llm_settings["temperature"],
            max_tokens=llm_settings["max_tokens"],
            base_url=llm_settings["base_url"],
            api_key=llm_settings["api_key"],
        )
        try:
            payload = _extract_json_object(content_text)
            comments = payload.get("comments")
            flags = payload.get("flags")
            if not isinstance(comments, list):
                comments = [str(comments)] if comments else [content_text]
            if not isinstance(flags, list):
                flags = []
        except Exception:
            comments = [content_text]
            flags = []
        item = {
            "comments": comments,
            "flags": flags,
            "metadata": {
                "review_tone": tone,
                "extension": "fair.core",
                "model": llm_settings["model"],
            },
        }
        await ctx.submission_result(submission.submission_id, item)
        return {"submission_id": submission.submission_id, **item}

    results = await asyncio.gather(*(_review_submission(submission) for submission in params.submissions))
    await ctx.progress(90, "Finalizing review")
    return {
        "plugin_type": "reviewer",
        "results": results,
        "metadata": {"completed_by": "fair.core.reviewer.simple"},
    }



app = core_extension.app
