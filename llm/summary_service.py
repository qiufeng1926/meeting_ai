"""
双轨总结：Markdown 速览 + 图文 JSON（并行生成，图文失败可重试）
"""
import asyncio
from dataclasses import dataclass

from config.config import visual_summary_retry_max
from llm.glm_chat import GLMClient
from llm.visual_schema import VisualSummary, parse_visual_summary, visual_summary_to_dict, visual_summary_to_json
from utils.logger import get_logger

logger = get_logger("summary_service")


@dataclass
class DualSummaryResult:
    markdown: str | None
    markdown_error: str | None
    visual: VisualSummary | None
    visual_json: str | None
    visual_status: str  # completed | failed | skipped
    visual_error: str | None


async def _generate_visual_with_retry(
    client: GLMClient,
    transcript: str,
    meeting_name: str | None,
    max_retries: int,
) -> tuple[VisualSummary | None, str | None, str | None]:
    last_error = None
    for attempt in range(max_retries + 1):
        try:
            raw = await client.summary_visual_async(transcript, meeting_name)
            visual = parse_visual_summary(raw)
            return visual, visual_summary_to_json(visual), None
        except Exception as e:
            last_error = str(e)
            logger.warning(
                f"图文速览生成失败 (attempt {attempt + 1}/{max_retries + 1}): {last_error}"
            )
            if attempt < max_retries:
                await asyncio.sleep(1)
    return None, None, last_error


async def generate_dual_summaries(
    client: GLMClient,
    transcript: str,
    meeting_name: str | None = None,
) -> DualSummaryResult:
    """并行生成 Markdown 与图文 JSON；Markdown 失败则整体失败，图文失败可重试后标 failed"""
    markdown_task = asyncio.create_task(client.summary_meeting_async(transcript))
    visual_task = asyncio.create_task(
        _generate_visual_with_retry(client, transcript, meeting_name, visual_summary_retry_max)
    )

    markdown_result, visual_result = await asyncio.gather(
        markdown_task, visual_task, return_exceptions=True
    )

    markdown = None
    markdown_error = None
    if isinstance(markdown_result, Exception):
        markdown_error = str(markdown_result)
        logger.error(f"Markdown 速览生成失败: {markdown_error}")
    else:
        markdown = markdown_result

    visual = None
    visual_json = None
    visual_status = 'failed'
    visual_error = None

    if isinstance(visual_result, Exception):
        visual_error = str(visual_result)
    else:
        visual, visual_json, visual_error = visual_result
        visual_status = 'completed' if visual else 'failed'

    if not transcript or not transcript.strip():
        visual_status = 'skipped'
        visual_error = visual_error or '转写为空'

    return DualSummaryResult(
        markdown=markdown,
        markdown_error=markdown_error,
        visual=visual,
        visual_json=visual_json,
        visual_status=visual_status,
        visual_error=visual_error,
    )


def dual_result_to_db_fields(result: DualSummaryResult) -> dict:
    """写入 meetings 表的字段"""
    return {
        'summary': result.markdown,
        'summary_visual': result.visual_json,
        'summary_visual_status': result.visual_status,
    }


def visual_dict_from_result(result: DualSummaryResult) -> dict | None:
    if result.visual:
        return visual_summary_to_dict(result.visual)
    if result.visual_json:
        import json
        try:
            return json.loads(result.visual_json)
        except json.JSONDecodeError:
            return None
    return None
