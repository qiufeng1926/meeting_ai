import os
import uuid
import time
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
from utils.logger import get_logger, log_api_call

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
    start_time = time.time()
    request_id = str(uuid.uuid4())
    
    # 记录请求参数
    input_params = {
        "filename": file.filename,
        "content_type": file.content_type,
        "meeting_name": meeting_name,
    }
    
    logger.info(f"[{request_id}] 收到音频文件上传请求", extra={'input_params': input_params, 'request_id': request_id})
    
    try:
        # 处理会议名称
        if meeting_name:
            safe_name = "".join(c for c in meeting_name if c.isalnum() or c in (' ', '-', '_')).strip()
            safe_name = safe_name.replace(' ', '_')
            name_prefix = f"{safe_name}_"
        else:
            name_prefix = ""

        # 生成文件名
        file_id = str(uuid.uuid4())
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        ext = file.filename.split(".")[-1]

        # 保存上传的音频文件
        save_path = os.path.join(upload_dir, f"{file_id}.{ext}")
        with open(save_path, "wb") as f:
            content = await file.read()
            f.write(content)
        logger.info(f"[{request_id}] 音频文件已保存: {save_path}", extra={'request_id': request_id})

        # ASR 语音转文字
        logger.info(f"[{request_id}] 开始语音识别...", extra={'request_id': request_id})
        transcript = asr_engine.transcribe(save_path)
        logger.info(f"[{request_id}] 语音识别完成，文本长度: {len(transcript)} 字符", extra={'request_id': request_id})

        # 保存转写文本
        transcript_path = os.path.join(output_dir, "transcripts", f"{name_prefix}{file_id}_{timestamp}.txt")
        with open(transcript_path, "w", encoding="utf-8") as f:
            f.write(transcript)
        logger.info(f"[{request_id}] 转写文本已保存: {transcript_path}", extra={'request_id': request_id})

        # AI 总结会议纪要
        logger.info(f"[{request_id}] 开始生成会议纪要...", extra={'request_id': request_id})
        summary = glm.summary_meeting(transcript)
        logger.info(f"[{request_id}] 会议纪要生成完成，长度: {len(summary)} 字符", extra={'request_id': request_id})

        # 保存会议纪要
        summary_path = os.path.join(output_dir, "summaries", f"{name_prefix}{file_id}_{timestamp}.md")
        with open(summary_path, "w", encoding="utf-8") as f:
            f.write(summary)
        logger.info(f"[{request_id}] 会议纪要已保存: {summary_path}", extra={'request_id': request_id})

        # 计算耗时
        duration_ms = (time.time() - start_time) * 1000
        
        # 准备输出参数（不包含完整文本，避免日志过大）
        output_params = {
            "success": True,
            "file_id": file_id,
            "transcript_length": len(transcript),
            "summary_length": len(summary),
            "transcript_file": transcript_path,
            "summary_file": summary_path,
            "duration_ms": round(duration_ms, 2)
        }
        
        logger.info(f"[{request_id}] 会议处理完成", extra={'output_params': output_params, 'request_id': request_id, 'duration_ms': duration_ms})
        
        return {
            "success": True,
            "filename": file.filename,
            "file_id": file_id,
            "transcript": transcript,
            "summary": summary,
            "transcript_file": transcript_path,
            "summary_file": summary_path
        }
        
    except Exception as e:
        duration_ms = (time.time() - start_time) * 1000
        error_params = {
            "error": str(e),
            "error_type": type(e).__name__,
            "duration_ms": round(duration_ms, 2)
        }
        logger.error(f"[{request_id}] 会议处理失败", exc_info=True, extra={'input_params': input_params, 'output_params': error_params, 'request_id': request_id, 'duration_ms': duration_ms})
        return {
            "success": False,
            "error": f"处理失败: {str(e)}"
        }
