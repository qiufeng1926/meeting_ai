from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from api.routes.meeting import router as meeting_router
from api.routes.websocket import router as websocket_router
from utils.logger import setup_logging
import os

# 初始化日志系统
logger = setup_logging(
    service_name="meeting_ai",
    console=True,
)

app = FastAPI(
    title="Meeting AI",
    version="1.0.0",
    description="会议 AI 系统 - 支持批量和实时语音转文本"
)

logger.info("Meeting AI 服务启动")

# 注册路由
app.include_router(meeting_router, prefix="/api", tags=["会议处理"])
app.include_router(websocket_router, prefix="/api", tags=["实时转写"])

# 挂载静态文件目录
static_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")
    logger.info(f"静态文件目录已挂载: {static_dir}")


@app.get("/")
async def root():
    """首页 - 重定向到实时转写页面"""
    html_path = os.path.join(static_dir, "transcribe.html")
    if os.path.exists(html_path):
        return FileResponse(html_path)
    return {"message": "Meeting AI API", "docs": "/docs"}