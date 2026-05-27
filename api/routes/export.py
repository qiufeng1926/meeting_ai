"""AI 总结导出 API"""
import os
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field

from api.auth_utils import get_current_user
from config.config import output_dir
from db.models import User
from db.session import check_meeting_access, get_meeting_by_file_id
from utils.docx_export import build_export_filename, markdown_to_docx
from utils.logger import get_logger

router = APIRouter()
logger = get_logger("export_route")


class SummaryExportRequest(BaseModel):
    content: str = Field(..., min_length=1)
    title: str = Field(default="AI 智能速览", max_length=100)


def _docx_response(content: str, title: str, file_id: str | None = None) -> Response:
    docx_bytes = markdown_to_docx(content, title=title)
    filename = build_export_filename(title, file_id)
    encoded = quote(filename)
    return Response(
        content=docx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={
            "Content-Disposition": f"attachment; filename=\"{encoded}\"; filename*=UTF-8''{encoded}",
        },
    )


def _load_summary_for_meeting(file_id: str) -> tuple[str, str]:
    meeting = get_meeting_by_file_id(file_id)
    title = "AI 智能速览"
    summary = None

    if meeting:
        if meeting.meeting_name:
            title = meeting.meeting_name
        if meeting.summary:
            summary = meeting.summary

    if not summary:
        summaries_dir = os.path.join(output_dir, "summaries")
        if os.path.isdir(summaries_dir):
            for name in os.listdir(summaries_dir):
                if file_id in name and name.endswith(".md"):
                    path = os.path.join(summaries_dir, name)
                    with open(path, "r", encoding="utf-8") as f:
                        summary = f.read()
                    break

    if not summary:
        raise HTTPException(status_code=404, detail="该会议暂无 AI 总结")

    return summary, title


@router.get("/meetings/{file_id}/export/summary")
async def export_meeting_summary_docx(
    file_id: str,
    current_user: User = Depends(get_current_user),
):
    """导出指定会议的 AI 总结为 Word 文档"""
    exists, allowed = check_meeting_access(file_id, current_user)
    if not exists:
        raise HTTPException(status_code=404, detail="会议不存在")
    if not allowed:
        raise HTTPException(status_code=403, detail="无权导出该会议")

    summary, title = _load_summary_for_meeting(file_id)
    logger.info(f"导出 AI 总结: file_id={file_id}, user={current_user.username}")
    return _docx_response(summary, title, file_id)


@router.post("/export/summary")
async def export_summary_content_docx(
    body: SummaryExportRequest,
    current_user: User = Depends(get_current_user),
):
    """根据总结正文直接导出 Word（用于刚生成尚未跳转历史的场景）"""
    logger.info(f"导出 AI 总结内容: user={current_user.username}, title={body.title}")
    return _docx_response(body.content.strip(), body.title.strip() or "AI 智能速览")
