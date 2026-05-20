import os
import uuid
from datetime import datetime

from fastapi import (
    APIRouter,
    UploadFile,
    File,
    Form
)

from config.config import upload_dir, output_dir
from asr.engine import FunASREngine
from llm.glm_chat import GLMClient
from utils.logger import get_logger

router = APIRouter()
logger = get_logger("meeting_route")

# 初始化
asr_engine = FunASREngine()
glm = GLMClient()

# 创建目录结构
os.makedirs(upload_dir, exist_ok=True)
os.makedirs(os.path.join(output_dir, "transcripts"), exist_ok=True)
os.makedirs(os.path.join(output_dir, "summaries"), exist_ok=True)


@router.post("/meeting/upload")
async def upload_meeting_audio(
    file: UploadFile = File(...),
    meeting_name: str = Form(None)
):
    logger.info(f"收到音频文件上传请求: {file.filename}")
    
    # 处理会议名称
    if meeting_name:
        # 清理文件名中的非法字符
        safe_name = "".join(c for c in meeting_name if c.isalnum() or c in (' ', '-', '_')).strip()
        safe_name = safe_name.replace(' ', '_')
        name_prefix = f"{safe_name}_"
        logger.info(f"会议名称: {meeting_name}")
    else:
        name_prefix = ""

    # 生成文件名
    file_id = str(uuid.uuid4())
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    ext = file.filename.split(".")[-1]

    # 保存上传的音频文件
    save_path = os.path.join(
        upload_dir,
        f"{file_id}.{ext}"
    )

    try:
        with open(save_path, "wb") as f:
            content = await file.read()
            f.write(content)
        logger.info(f"音频文件已保存: {save_path}")
    except Exception as e:
        logger.error(f"保存音频文件失败: {e}", exc_info=True)
        return {
            "success": False,
            "error": f"保存文件失败: {str(e)}"
        }

    # ASR 语音转文字
    try:
        logger.info("开始语音识别...")
        transcript = asr_engine.transcribe(save_path)
        logger.info(f"语音识别完成，文本长度: {len(transcript)} 字符")
    except Exception as e:
        logger.error(f"语音识别失败: {e}", exc_info=True)
        return {
            "success": False,
            "error": f"语音识别失败: {str(e)}"
        }

    # 保存转写文本
    transcript_path = os.path.join(
        output_dir, "transcripts",
        f"{name_prefix}{file_id}_{timestamp}.txt"
    )
    try:
        with open(transcript_path, "w", encoding="utf-8") as f:
            f.write(transcript)
        logger.info(f"转写文本已保存: {transcript_path}")
    except Exception as e:
        logger.error(f"保存转写文本失败: {e}", exc_info=True)

    # AI 总结会议纪要
    try:
        logger.info("开始生成会议纪要...")
        summary = glm.summary_meeting(transcript)
        logger.info(f"会议纪要生成完成，长度: {len(summary)} 字符")
    except Exception as e:
        logger.error(f"生成会议纪要失败: {e}", exc_info=True)
        return {
            "success": False,
            "error": f"生成会议纪要失败: {str(e)}"
        }

    # 保存会议纪要
    summary_path = os.path.join(
        output_dir, "summaries",
        f"{name_prefix}{file_id}_{timestamp}.md"
    )
    try:
        with open(summary_path, "w", encoding="utf-8") as f:
            f.write(summary)
        logger.info(f"会议纪要已保存: {summary_path}")
    except Exception as e:
        logger.error(f"保存会议纪要失败: {e}", exc_info=True)

    logger.info(f"会议处理完成: file_id={file_id}")
    return {
        "success": True,
        "filename": file.filename,
        "file_id": file_id,
        "transcript": transcript,
        "summary": summary,
        "transcript_file": transcript_path,
        "summary_file": summary_path
    }
