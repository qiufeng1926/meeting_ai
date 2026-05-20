import os
import uuid
import time
import asyncio
from datetime import datetime
from pathlib import Path

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
    """
    异步批量上传音频文件并处理
    """
    start_time = time.time()
    request_id = str(uuid.uuid4())
    
    # 记录请求参数
    input_params = {
        "filename": file.filename,
        "content_type": file.content_type,
        "file_size": None,  # 稍后填充
        "meeting_name": meeting_name,
    }
    
    logger.info(f"收到音频文件上传请求", extra={'request_id': request_id, 'input_params': input_params})
    
    try:
        # 读取文件内容
        content = await file.read()
        input_params["file_size"] = len(content)
        
        # 处理会议名称
        if meeting_name:
            safe_name = "".join(c for c in meeting_name if c.isalnum() or c in (' ', '-', '_')).strip()
            safe_name = safe_name.replace(' ', '_')
            name_prefix = f"{safe_name}_"
            logger.info(f"设置会议名称", extra={'request_id': request_id, 'input_params': {'meeting_name': meeting_name, 'safe_name': safe_name}})
        else:
            name_prefix = ""

        # 生成文件名
        file_id = str(uuid.uuid4())
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        ext = file.filename.split(".")[-1]

        # 异步保存上传的音频文件
        save_path = os.path.join(upload_dir, f"{file_id}.{ext}")
        await _save_file_async(save_path, content)
        logger.info(f"音频文件已保存", extra={'request_id': request_id, 'output_params': {'save_path': save_path, 'file_size': len(content)}})

        # 异步 ASR 语音转文字
        logger.info(f"开始语音识别...", extra={'request_id': request_id})
        asr_start = time.time()
        transcript = await asr_engine.transcribe_async(save_path)
        asr_duration = (time.time() - asr_start) * 1000
        logger.info(f"语音识别完成", extra={
            'request_id': request_id, 
            'output_params': {
                'transcript_length': len(transcript),
                'asr_duration_ms': round(asr_duration, 2)
            }
        })

        # 异步保存转写文本
        transcript_path = os.path.join(output_dir, "transcripts", f"{name_prefix}{file_id}_{timestamp}.txt")
        await _save_text_async(transcript_path, transcript)
        logger.info(f"转写文本已保存", extra={'request_id': request_id, 'output_params': {'transcript_file': transcript_path}})

        # 异步 AI 总结会议纪要
        logger.info(f"开始生成会议纪要...", extra={'request_id': request_id})
        llm_start = time.time()
        summary = await glm.summary_meeting_async(transcript)
        llm_duration = (time.time() - llm_start) * 1000
        logger.info(f"会议纪要生成完成", extra={
            'request_id': request_id,
            'output_params': {
                'summary_length': len(summary),
                'llm_duration_ms': round(llm_duration, 2)
            }
        })

        # 异步保存会议纪要
        summary_path = os.path.join(output_dir, "summaries", f"{name_prefix}{file_id}_{timestamp}.md")
        await _save_text_async(summary_path, summary)
        logger.info(f"会议纪要已保存", extra={'request_id': request_id, 'output_params': {'summary_file': summary_path}})

        # 计算总耗时
        total_duration_ms = (time.time() - start_time) * 1000
        
        # 准备输出参数
        output_params = {
            "success": True,
            "file_id": file_id,
            "transcript_length": len(transcript),
            "summary_length": len(summary),
            "transcript_file": transcript_path,
            "summary_file": summary_path,
            "total_duration_ms": round(total_duration_ms, 2),
            "asr_duration_ms": round(asr_duration, 2),
            "llm_duration_ms": round(llm_duration, 2)
        }
        
        logger.info(f"会议处理完成", extra={'request_id': request_id, 'input_params': input_params, 'output_params': output_params, 'duration_ms': total_duration_ms})
        
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
        total_duration_ms = (time.time() - start_time) * 1000
        error_params = {
            "error": str(e),
            "error_type": type(e).__name__,
            "duration_ms": round(total_duration_ms, 2)
        }
        logger.error(f"会议处理失败", exc_info=True, extra={'request_id': request_id, 'input_params': input_params, 'output_params': error_params, 'duration_ms': total_duration_ms})
        return {
            "success": False,
            "error": f"处理失败: {str(e)}"
        }


async def _save_file_async(file_path: str, content: bytes):
    """异步保存文件"""
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, lambda: Path(file_path).write_bytes(content))


async def _save_text_async(file_path: str, text: str):
    """异步保存文本文件"""
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, lambda: Path(file_path).write_text(text, encoding='utf-8'))
