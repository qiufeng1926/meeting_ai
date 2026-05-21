import json
import uuid
import os
import time
import asyncio
from pathlib import Path
from datetime import datetime
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from utils.logger import get_logger
from asr.engine import FunASREngine
from llm.glm_chat import GLMClient
from config.config import output_dir

router = APIRouter()
logger = get_logger("websocket_route")

# 初始化引擎
asr_engine = FunASREngine()
glm_client = GLMClient()


class ConnectionManager:
    """管理 WebSocket 连接"""
    
    def __init__(self):
        self.active_connections: dict[str, WebSocket] = {}
    
    async def connect(self, websocket: WebSocket, connection_id: str):
        await websocket.accept()
        self.active_connections[connection_id] = websocket
        logger.info(f"WebSocket 连接建立", extra={'request_id': connection_id, 'output_params': {'connection_id': connection_id}})
    
    def disconnect(self, connection_id: str):
        if connection_id in self.active_connections:
            del self.active_connections[connection_id]
            logger.info(f"WebSocket 连接断开", extra={'request_id': connection_id})
    
    async def send_json(self, connection_id: str, data: dict) -> bool:
        ws = self.active_connections.get(connection_id)
        if ws is None:
            return False
        try:
            await ws.send_json(data)
            return True
        except WebSocketDisconnect:
            self.disconnect(connection_id)
            return False
        except RuntimeError:
            self.disconnect(connection_id)
            return False


manager = ConnectionManager()


@router.websocket("/ws/transcribe")
async def websocket_transcribe(websocket: WebSocket):
    """
    WebSocket 实时语音转文本
    客户端发送音频数据块，服务端返回识别结果
    """
    start_time = time.time()
    connection_id = str(uuid.uuid4())
    await manager.connect(websocket, connection_id)
    
    # 会话信息（每连接独立的流式识别器，含 VAD 与音频缓冲）
    transcriber = asr_engine.create_streaming_session()
    session_info = {
        "connection_id": connection_id,
        "start_time": datetime.now().isoformat(),
        "total_text": "",
        "file_id": None,
        "meeting_name": None,
        "audio_chunks": 0,
        "transcriber": transcriber,
    }
    
    logger.info(f"开始实时语音转写会话", extra={'request_id': connection_id, 'input_params': {'connection_id': connection_id}})
    
    try:
        while True:
            # 接收客户端消息（前端使用 JSON 文本帧，非二进制）
            raw_message = await websocket.receive()
            if raw_message.get("type") == "websocket.disconnect":
                raise WebSocketDisconnect()

            if "text" in raw_message:
                data = raw_message["text"].encode("utf-8")
            elif "bytes" in raw_message:
                data = raw_message["bytes"]
            else:
                continue

            if len(data) < 1:
                continue
            
            try:
                # 尝试解析 JSON 元数据 + 音频数据
                message = json.loads(data.decode('utf-8', errors='ignore'))
                
                # 处理初始化消息（会议名称）
                if message.get("type") == "init":
                    meeting_name = message.get("meeting_name", "")
                    if meeting_name:
                        session_info["meeting_name"] = meeting_name
                        logger.info(f"设置会议名称", extra={'request_id': connection_id, 'input_params': {'meeting_name': meeting_name}})
                    continue
                
                if message.get("type") == "audio":
                    audio_bytes = bytes(message.get("data", []))
                    sample_rate = message.get("sample_rate", 16000)
                    session_info["audio_chunks"] += 1
                    
                    text = await asr_engine.feed_stream_async(
                        session_info["transcriber"], audio_bytes, sample_rate
                    )
                    
                    if text:
                        session_info["total_text"] += text
                        result = {
                            "type": "result",
                            "text": text,
                            "total_text": session_info["total_text"],
                            "timestamp": datetime.now().isoformat(),
                        }
                        if not await manager.send_json(connection_id, result):
                            raise WebSocketDisconnect()
                        
                elif message.get("type") == "end":
                    # 冲刷缓冲区中剩余音频
                    final_text = await asr_engine.finalize_stream_async(
                        session_info["transcriber"]
                    )
                    if final_text:
                        session_info["total_text"] += final_text
                        await manager.send_json(connection_id, {
                            "type": "result",
                            "text": final_text,
                            "total_text": session_info["total_text"],
                            "timestamp": datetime.now().isoformat(),
                        })

                    # 会话结束，生成 AI 总结
                    duration_ms = (time.time() - start_time) * 1000
                    logger.info(f"会话结束，开始生成 AI 总结", extra={'request_id': connection_id, 'output_params': {'duration_ms': round(duration_ms, 2), 'total_text_length': len(session_info["total_text"]), 'audio_chunks': session_info["audio_chunks"]}})
                    
                    # 保存转写文本
                    file_id = str(uuid.uuid4())
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    session_info["file_id"] = file_id
                    
                    # 构建文件名（包含会议名称）
                    meeting_name = session_info.get("meeting_name", "")
                    if meeting_name:
                        # 清理文件名中的非法字符
                        safe_name = "".join(c for c in meeting_name if c.isalnum() or c in (' ', '-', '_')).strip()
                        safe_name = safe_name.replace(' ', '_')
                        transcript_filename = f"{safe_name}_{file_id}_{timestamp}_realtime.txt"
                        summary_filename = f"{safe_name}_{file_id}_{timestamp}_realtime.md"
                    else:
                        transcript_filename = f"{file_id}_{timestamp}_realtime.txt"
                        summary_filename = f"{file_id}_{timestamp}_realtime.md"
                    
                    # 异步保存转写文本
                    transcript_path = os.path.join(
                        output_dir, "transcripts",
                        transcript_filename
                    )
                    await _save_text_async(transcript_path, session_info["total_text"])
                    logger.info(f"实时转写文本已保存", extra={'request_id': connection_id, 'output_params': {'transcript_file': transcript_path, 'text_length': len(session_info["total_text"])}})
                    
                    end_result_base = {
                        "total_text": session_info["total_text"],
                        "file_id": file_id,
                        "transcript_file": transcript_path,
                        "duration": str(
                            datetime.now()
                            - datetime.fromisoformat(session_info["start_time"])
                        ),
                    }

                    # 发送正在生成总结的消息
                    if not await manager.send_json(connection_id, {
                        "type": "generating_summary",
                        "message": "正在生成 AI 会议纪要...",
                    }):
                        logger.info(
                            "客户端已断开，跳过 AI 总结推送",
                            extra={"request_id": connection_id},
                        )
                        break

                    # 异步生成 AI 总结
                    try:
                        summary = await glm_client.summary_meeting_async(
                            session_info["total_text"]
                        )

                        summary_path = os.path.join(
                            output_dir, "summaries", summary_filename
                        )
                        await _save_text_async(summary_path, summary)

                        total_duration_ms = (time.time() - start_time) * 1000
                        logger.info(
                            "实时会议纪要已保存",
                            extra={
                                "request_id": connection_id,
                                "output_params": {
                                    "summary_file": summary_path,
                                    "summary_length": len(summary),
                                    "total_duration_ms": round(total_duration_ms, 2),
                                },
                            },
                        )

                        end_result = {
                            "type": "session_end",
                            "summary": summary,
                            "summary_file": summary_path,
                            **end_result_base,
                        }
                        await manager.send_json(connection_id, end_result)

                    except Exception as e:
                        total_duration_ms = (time.time() - start_time) * 1000
                        logger.error(
                            "生成 AI 总结失败",
                            exc_info=True,
                            extra={
                                "request_id": connection_id,
                                "output_params": {
                                    "error": str(e),
                                    "error_type": type(e).__name__,
                                    "duration_ms": round(total_duration_ms, 2),
                                },
                            },
                        )
                        end_result = {
                            "type": "session_end",
                            "summary": None,
                            "error": f"生成总结失败: {str(e)}",
                            **end_result_base,
                        }
                        await manager.send_json(connection_id, end_result)

                    break
                    
            except (json.JSONDecodeError, UnicodeDecodeError):
                # 原始 PCM 二进制帧
                try:
                    text = await asr_engine.feed_stream_async(
                        session_info["transcriber"], data, 16000
                    )
                    if text:
                        session_info["total_text"] += text
                        await manager.send_json(connection_id, {
                            "type": "result",
                            "text": text,
                            "total_text": session_info["total_text"],
                            "timestamp": datetime.now().isoformat(),
                        })
                except Exception as e:
                    logger.error(f"处理音频数据失败: {e}")
                    await manager.send_json(connection_id, {
                        "type": "error",
                        "message": f"处理失败: {str(e)}",
                    })
    
    except WebSocketDisconnect:
        duration_ms = (time.time() - start_time) * 1000
        logger.info(f"WebSocket 断开连接", extra={'request_id': connection_id, 'output_params': {'duration_ms': round(duration_ms, 2), 'total_text_length': len(session_info["total_text"]), 'audio_chunks': session_info["audio_chunks"]}})
    except RuntimeError as e:
        if "close message" in str(e).lower():
            logger.info(f"WebSocket 已关闭", extra={'request_id': connection_id})
        else:
            raise
    except Exception as e:
        duration_ms = (time.time() - start_time) * 1000
        logger.error(f"WebSocket 错误", exc_info=True, extra={'request_id': connection_id, 'output_params': {'error': str(e), 'error_type': type(e).__name__, 'duration_ms': round(duration_ms, 2)}})
    finally:
        manager.disconnect(connection_id)
        logger.info(f"会话清理完成", extra={'request_id': connection_id})


@router.get("/ws/status")
async def websocket_status():
    """获取 WebSocket 连接状态"""
    return {
        "active_connections": len(manager.active_connections),
        "connections": list(manager.active_connections.keys())
    }


@router.get("/meetings/list")
async def list_meetings():
    """获取已保存的会议列表"""
    start_time = time.time()
    request_id = str(uuid.uuid4())
    
    logger.info(f"获取会议列表请求", extra={'request_id': request_id})
    
    try:
        transcripts_dir = os.path.join(output_dir, "transcripts")
        summaries_dir = os.path.join(output_dir, "summaries")
        
        meetings = []
        
        # 获取所有转写文件
        if os.path.exists(transcripts_dir):
            for filename in sorted(os.listdir(transcripts_dir), reverse=True):
                if filename.endswith('.txt'):
                    file_id = filename.split('_')[0]
                    filepath = os.path.join(transcripts_dir, filename)
                    
                    # 获取文件信息
                    stat = os.stat(filepath)
                    created_time = datetime.fromtimestamp(stat.st_ctime).isoformat()
                    
                    # 查找对应的总结文件
                    summary_filename = filename.replace('.txt', '.md')
                    summary_path = os.path.join(summaries_dir, summary_filename)
                    has_summary = os.path.exists(summary_path)
                    
                    # 读取部分内容作为预览
                    with open(filepath, 'r', encoding='utf-8') as f:
                        preview = f.read(200)  # 前200字符
                    
                    meetings.append({
                        "file_id": file_id,
                        "filename": filename,
                        "created_at": created_time,
                        "size": stat.st_size,
                        "has_summary": has_summary,
                        "preview": preview,
                        "transcript_file": filepath,
                        "summary_file": summary_path if has_summary else None
                    })
        
        duration_ms = (time.time() - start_time) * 1000
        output_params = {
            "success": True,
            "total": len(meetings),
            "duration_ms": round(duration_ms, 2)
        }
        logger.info(f"获取会议列表成功", extra={'request_id': request_id, 'output_params': output_params, 'duration_ms': duration_ms})
        
        return {
            "success": True,
            "total": len(meetings),
            "meetings": meetings
        }
        
    except Exception as e:
        duration_ms = (time.time() - start_time) * 1000
        error_params = {"error": str(e), "error_type": type(e).__name__, "duration_ms": round(duration_ms, 2)}
        logger.error(f"获取会议列表失败", exc_info=True, extra={'request_id': request_id, 'output_params': error_params, 'duration_ms': duration_ms})
        return {
            "success": False,
            "error": str(e)
        }


@router.get("/meetings/{file_id}")
async def get_meeting(file_id: str):
    """获取指定会议的详细内容"""
    start_time = time.time()
    request_id = str(uuid.uuid4())
    
    input_params = {"file_id": file_id}
    logger.info(f"获取会议详情请求", extra={'request_id': request_id, 'input_params': input_params})
    
    try:
        transcripts_dir = os.path.join(output_dir, "transcripts")
        summaries_dir = os.path.join(output_dir, "summaries")
        
        # 查找文件
        transcript_file = None
        summary_file = None
        
        for filename in os.listdir(transcripts_dir):
            if filename.startswith(file_id):
                transcript_file = os.path.join(transcripts_dir, filename)
                summary_filename = filename.replace('.txt', '.md')
                summary_path = os.path.join(summaries_dir, summary_filename)
                if os.path.exists(summary_path):
                    summary_file = summary_path
                break
        
        if not transcript_file:
            duration_ms = (time.time() - start_time) * 1000
            error_params = {"error": "会议不存在", "duration_ms": round(duration_ms, 2)}
            logger.warning(f"会议不存在", extra={'request_id': request_id, 'input_params': input_params, 'output_params': error_params, 'duration_ms': duration_ms})
            return {
                "success": False,
                "error": "会议不存在"
            }
        
        # 读取内容
        with open(transcript_file, 'r', encoding='utf-8') as f:
            transcript = f.read()
        
        summary = None
        if summary_file:
            with open(summary_file, 'r', encoding='utf-8') as f:
                summary = f.read()
        
        duration_ms = (time.time() - start_time) * 1000
        output_params = {
            "success": True,
            "file_id": file_id,
            "transcript_length": len(transcript),
            "has_summary": summary is not None,
            "summary_length": len(summary) if summary else 0,
            "duration_ms": round(duration_ms, 2)
        }
        logger.info(f"获取会议详情成功", extra={'request_id': request_id, 'input_params': input_params, 'output_params': output_params, 'duration_ms': duration_ms})
        
        return {
            "success": True,
            "file_id": file_id,
            "transcript": transcript,
            "summary": summary,
            "transcript_file": transcript_file,
            "summary_file": summary_file
        }
        
    except Exception as e:
        duration_ms = (time.time() - start_time) * 1000
        error_params = {"error": str(e), "error_type": type(e).__name__, "duration_ms": round(duration_ms, 2)}
        logger.error(f"获取会议详情失败", exc_info=True, extra={'request_id': request_id, 'input_params': input_params, 'output_params': error_params, 'duration_ms': duration_ms})
        return {
            "success": False,
            "error": str(e)
        }


async def _save_text_async(file_path: str, text: str):
    """异步保存文本文件"""
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, lambda: Path(file_path).write_text(text, encoding='utf-8'))
