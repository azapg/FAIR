import os

from pydantic import BaseModel, Field

from fair_platform.extension_sdk import FairExtension, JobContext


class RubricParams(BaseModel):
    instruction: str = Field(min_length=1)


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
)


@core_extension.action("rubric.create")
async def create_rubric(ctx: JobContext, params: RubricParams) -> dict:
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


app = core_extension.app
