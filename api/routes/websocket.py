import json
import uuid
import os
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
        logger.info(f"WebSocket 连接建立: {connection_id}")
    
    def disconnect(self, connection_id: str):
        if connection_id in self.active_connections:
            del self.active_connections[connection_id]
            logger.info(f"WebSocket 连接断开: {connection_id}")
    
    async def send_json(self, connection_id: str, data: dict):
        if connection_id in self.active_connections:
            await self.active_connections[connection_id].send_json(data)


manager = ConnectionManager()


@router.websocket("/ws/transcribe")
async def websocket_transcribe(websocket: WebSocket):
    """
    WebSocket 实时语音转文本
    客户端发送音频数据块，服务端返回识别结果
    """
    connection_id = str(uuid.uuid4())
    await manager.connect(websocket, connection_id)
    
    # 会话信息
    session_info = {
        "connection_id": connection_id,
        "start_time": datetime.now().isoformat(),
        "total_text": "",
        "file_id": None,
        "meeting_name": None
    }
    
    logger.info(f"开始实时语音转写会话: {connection_id}")
    
    try:
        while True:
            # 接收客户端消息
            data = await websocket.receive_bytes()
            
            # 解析消息（假设第一个字节是消息类型）
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
                        logger.info(f"设置会议名称: {meeting_name}")
                    continue
                
                if message.get("type") == "audio":
                    audio_bytes = bytes(message.get("data", []))
                    sample_rate = message.get("sample_rate", 16000)
                    
                    # 进行语音识别
                    text = asr_engine.transcribe_stream(audio_bytes, sample_rate)
                    
                    if text:
                        session_info["total_text"] += text
                        
                        # 发送识别结果
                        result = {
                            "type": "result",
                            "text": text,
                            "total_text": session_info["total_text"],
                            "timestamp": datetime.now().isoformat()
                        }
                        await manager.send_json(connection_id, result)
                        
                elif message.get("type") == "end":
                    # 会话结束，生成 AI 总结
                    logger.info(f"会话结束，开始生成 AI 总结: {connection_id}")
                    
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
                    
                    transcript_path = os.path.join(
                        output_dir, "transcripts",
                        transcript_filename
                    )
                    with open(transcript_path, "w", encoding="utf-8") as f:
                        f.write(session_info["total_text"])
                    logger.info(f"实时转写文本已保存: {transcript_path}")
                    
                    # 发送正在生成总结的消息
                    await manager.send_json(connection_id, {
                        "type": "generating_summary",
                        "message": "正在生成 AI 会议纪要..."
                    })
                    
                    # 生成 AI 总结
                    try:
                        summary = glm_client.summary_meeting(session_info["total_text"])
                        
                        # 保存会议纪要
                        summary_path = os.path.join(
                            output_dir, "summaries",
                            summary_filename
                        )
                        with open(summary_path, "w", encoding="utf-8") as f:
                            f.write(summary)
                        logger.info(f"实时会议纪要已保存: {summary_path}")
                        
                        # 发送最终结果
                        end_result = {
                            "type": "session_end",
                            "total_text": session_info["total_text"],
                            "summary": summary,
                            "file_id": file_id,
                            "transcript_file": transcript_path,
                            "summary_file": summary_path,
                            "duration": str(datetime.now() - datetime.fromisoformat(session_info["start_time"]))
                        }
                        await manager.send_json(connection_id, end_result)
                        
                    except Exception as e:
                        logger.error(f"生成 AI 总结失败: {e}", exc_info=True)
                        end_result = {
                            "type": "session_end",
                            "total_text": session_info["total_text"],
                            "summary": None,
                            "error": f"生成总结失败: {str(e)}",
                            "file_id": file_id,
                            "duration": str(datetime.now() - datetime.fromisoformat(session_info["start_time"]))
                        }
                        await manager.send_json(connection_id, end_result)
                    
                    break
                    
            except (json.JSONDecodeError, UnicodeDecodeError):
                # 如果无法解析为 JSON，直接当作 PCM 数据处理
                try:
                    text = asr_engine.transcribe_stream(data, sample_rate=16000)
                    
                    if text:
                        session_info["total_text"] += text
                        
                        result = {
                            "type": "result",
                            "text": text,
                            "total_text": session_info["total_text"],
                            "timestamp": datetime.now().isoformat()
                        }
                        await manager.send_json(connection_id, result)
                except Exception as e:
                    logger.error(f"处理音频数据失败: {e}")
                    error_msg = {
                        "type": "error",
                        "message": f"处理失败: {str(e)}"
                    }
                    await manager.send_json(connection_id, error_msg)
    
    except WebSocketDisconnect:
        logger.info(f"WebSocket 断开连接: {connection_id}")
    except Exception as e:
        logger.error(f"WebSocket 错误: {e}", exc_info=True)
    finally:
        manager.disconnect(connection_id)
        logger.info(f"会话清理完成: {connection_id}")


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
        
        return {
            "success": True,
            "total": len(meetings),
            "meetings": meetings
        }
        
    except Exception as e:
        logger.error(f"获取会议列表失败: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e)
        }


@router.get("/meetings/{file_id}")
async def get_meeting(file_id: str):
    """获取指定会议的详细内容"""
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
        
        return {
            "success": True,
            "file_id": file_id,
            "transcript": transcript,
            "summary": summary,
            "transcript_file": transcript_file,
            "summary_file": summary_file
        }
        
    except Exception as e:
        logger.error(f"获取会议详情失败: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e)
        }
