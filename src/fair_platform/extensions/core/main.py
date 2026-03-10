import asyncio
import os

from fair_platform.extension_sdk import (
    FairExtension,
    JobContext,
    PluginDescriptor,
    WorkflowStepExecutionRequest,
)
from fair_platform.extension_sdk.contracts.rubric import RubricJobRequest


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
            description="Creates a placeholder markdown transcription from submission metadata.",
            version="1.0.0",
            action="plugin.transcribe.simple",
            settings_schema={
                "title": "Simple Transcriber",
                "type": "object",
                "properties": {
                    "prefix": {
                        "title": "TextField",
                        "label": "Prefix",
                        "type": "string",
                        "description": "Prefix to include in the generated transcription.",
                        "default": "Transcription",
                    }
                },
            },
        ),
        PluginDescriptor(
            plugin_id="fair.core.grader.simple",
            extension_id=os.getenv("FAIR_CORE_EXTENSION_ID", "fair.core"),
            plugin_type="grader",
            name="Simple Grader",
            description="Assigns a basic score and feedback using the available transcription.",
            version="1.0.0",
            action="plugin.grade.simple",
            settings_schema={
                "title": "Simple Grader",
                "type": "object",
                "properties": {
                    "score": {
                        "title": "NumberField",
                        "label": "Score",
                        "type": "number",
                        "description": "Default score to assign.",
                        "default": 85,
                    }
                },
            },
        ),
        PluginDescriptor(
            plugin_id="fair.core.reviewer.simple",
            extension_id=os.getenv("FAIR_CORE_EXTENSION_ID", "fair.core"),
            plugin_type="reviewer",
            name="Simple Reviewer",
            description="Adds a lightweight review comment for each submission.",
            version="1.0.0",
            action="plugin.review.simple",
            settings_schema={
                "title": "Simple Reviewer",
                "type": "object",
                "properties": {
                    "reviewTone": {
                        "title": "TextField",
                        "label": "Review Tone",
                        "type": "string",
                        "description": "Tone to use in generated comments.",
                        "default": "concise",
                    }
                },
            },
        )
    ],
)


@core_extension.action("rubric.create")
async def create_rubric(ctx: JobContext, params: RubricJobRequest) -> dict:
    await ctx.progress(10, "Reading rubric instruction", status="running")
    await ctx.log("info", "Generating rubric draft")
    await ctx.progress(80, "Finalizing rubric")
    return {
        "content": {
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
    }


@core_extension.action("plugin.review.simple")
async def simple_reviewer(ctx: JobContext, params: WorkflowStepExecutionRequest) -> dict:
    await ctx.progress(10, "Preparing review step", status="running")
    tone = str(params.settings.get("reviewTone", "concise")).strip() or "concise"
    await ctx.log("info", f"Running simple reviewer with tone={tone}")

    async def _review_submission(submission):
        item = {
            "comments": [f"{tone.capitalize()} review completed for submission {submission.submission_id}."],
            "flags": [],
            "metadata": {"review_tone": tone, "extension": "fair.core"},
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


@core_extension.action("plugin.transcribe.simple")
async def simple_transcriber(ctx: JobContext, params: WorkflowStepExecutionRequest) -> dict:
    await ctx.progress(10, "Preparing transcription step", status="running")
    prefix = str(params.settings.get("prefix", "Transcription")).strip() or "Transcription"
    await ctx.log("info", f"Running simple transcriber with prefix={prefix}")

    async def _transcribe_submission(submission):
        item = {
            "transcription": f"# {prefix}\n\nSubmission {submission.submission_id} processed by fair.core.",
            "metadata": {"prefix": prefix, "extension": "fair.core"},
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
    await ctx.log("info", f"Running simple grader with score={score}")

    async def _grade_submission(submission):
        transcription = submission.state.transcription or "No transcription provided."
        item = {
            "grade": score,
            "feedback": f"Auto-graded by fair.core using transcription summary: {transcription[:120]}",
            "metadata": {"score": score, "extension": "fair.core"},
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


app = core_extension.app
